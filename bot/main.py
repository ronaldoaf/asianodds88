"""Loop principal (equivalente ao ciclo() do bot365_blogabet), apostando Under no intervalo via AsianOdds.

Uso:  python -m bot.main                  (simulação, padrão)
      SIMULACAO=false python -m bot.main  (apostas reais)
"""
import json
import time
import traceback
from pathlib import Path

from .casamento import Casador
from .config import Config
from .modelo import calc_index, perc_banca
from .models import parse_line
from .site import AsianOddsSite
from .stats import fetch_stats
from .strategy import Candidato, avaliar

DIA = 24 * 3600


class Estado:
    def __init__(self, path: str):
        self.path = Path(path)
        d = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.published = d.get("published", [])
        self.errors = d.get("errors", [])
        self.ultimo_ciclo = d.get("ultimo_ciclo")

    def save(self):
        agora = time.time()
        self.published = [p for p in self.published if p["timestamp"] > agora - 7 * DIA]
        self.path.write_text(json.dumps({"published": self.published, "errors": self.errors[-50:],
                                         "ultimo_ciclo": self.ultimo_ciclo}, ensure_ascii=False, indent=1),
                             encoding="utf-8")

    def ja_publicados(self) -> set:
        return {p["home_v_away"] for p in self.published if p["timestamp"] > time.time() - DIA}

    def apostado_hoje(self) -> float:
        hoje = time.strftime("%Y-%m-%d")
        return sum(p.get("valor", 0) for p in self.published
                   if not p.get("simulado") and not p.get("erro") and time.strftime("%Y-%m-%d", time.localtime(p["timestamp"])) == hoje)

    def erro(self, msg: str):
        print("ERRO:", msg)
        self.errors.append({"data": msg, "timestamp": time.time()})


def apostar(site: AsianOddsSite, c: Candidato, cfg: Config, banca: float, est: Estado) -> dict:
    """Abre o cupom, relê a odd da casa, recalcula índice/valor e (se não for simulação) aposta."""
    ln = c.line
    odds, idx = ln.ft_under, c.idx
    for tentativa in range(1, 4):
        slip = site.open_under_slip(ln.lid)
        if not slip:
            raise RuntimeError(f"Under {ln.ft_line_raw} não encontrado na grade em {c.key}")
        book = next((b for b in slip["books"] if b["code"] == cfg.bookie and b["checked"] and b["price"]), None)
        if not book:
            site.close_slip()
            raise RuntimeError(f"{cfg.bookie} sem preço no cupom de {c.key}")
        if book["line"] and parse_line(book["line"]) != ln.ft_line:
            site.close_slip()
            raise RuntimeError(f"Linha do cupom {book['line']} != {ln.ft_line_raw} em {c.key}")
        if book["price"] != odds:
            idx = calc_index(c.st, ln.ft_line, book["price"])
            print(f"   odd {odds} -> {book['price']} ({cfg.bookie}), idx {idx:.4f}")
            odds = book["price"]
        if odds < cfg.odds_minima:
            site.close_slip()
            raise RuntimeError(f"Cancelada em {c.key}: odd {odds} < odds_minima {cfg.odds_minima}")
        if not idx > cfg.minimo_indice_para_publicar:
            site.close_slip()
            raise RuntimeError(f"Cancelada em {c.key}: com odd {odds} o idx caiu para {idx:.4f}")
        perc = perc_banca(idx, cfg.percentual_de_kelly, cfg.maximo_da_banca_por_aposta)
        valor = round(max(perc * banca, book["min"] or 0), 2)
        if book["max"] and valor > book["max"]:
            valor = float(book["max"])
        if cfg.exposicao_max_dia and est.apostado_hoje() + valor > cfg.exposicao_max_dia:
            site.close_slip()
            raise RuntimeError(f"Exposição do dia atingida, não apostou em {c.key}")
        res = {"odds": odds, "idx": idx, "perc": perc, "valor": valor, "bookie": cfg.bookie}
        if cfg.simulacao:
            site.close_slip()
            return {**res, "simulado": True}
        r = site.place_open_slip(valor, odds)  # odd mínima = a odd lida: não aceita pior
        site.close_slip()
        if not r["error"]:
            return {**res, "mensagens": r["messages"][-5:]}
        if tentativa == 3 or not any(w in r["error"].lower() for w in ("odds", "price", "changed")):
            raise RuntimeError(f"Aposta não aceita em {c.key}: {r['error']}")
        print("   odd mudou no envio, tentando de novo:", r["error"])
    raise RuntimeError(f"Aposta não confirmada em {c.key}")


def ciclo(site: AsianOddsSite, cfg: Config, est: Estado, casador: Casador):
    stats = fetch_stats(cfg.licenca, cfg.usuario, cfg.max_idade_stats_min)
    lines = site.live_lines()
    cands, desc = avaliar(stats, lines, cfg, est.ja_publicados(), casador)
    est.ultimo_ciclo = {
        "timestamp": time.time(), "stats": len(stats), "linhas_ao": len(lines),
        "candidatos": [{"jogo": c.key, "asianodds": f"{c.partida.home} v {c.partida.away}",
                        "goalline": c.line.ft_line, "oddsU": c.line.ft_under, "idx": round(c.idx, 4)} for c in cands],
        "descartes": desc,
    }
    print(time.strftime("%H:%M:%S"), f"stats {len(stats)} | linhas {len(lines)} | candidatos {len(cands)}",
          {k: len(v) for k, v in desc.items() if v})
    for c in est.ultimo_ciclo["candidatos"]:
        print(f"   cand: {c['jogo']} -> {c['asianodds']} | U{c['goalline']} @{c['oddsU']} | idx {c['idx']}")
    for motivo, jogos in desc.items():
        if jogos and motivo != "ja_publicado":
            print(f"   {motivo}: {'; '.join(jogos)}")
    if stats:
        idades = [(time.time() - float(s.get("ts") or 0)) / 60 for s in stats]
        print(f"   idade das stats: {min(idades):.1f} a {max(idades):.1f} min")
        with open("ciclos.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(est.ultimo_ciclo, ensure_ascii=False) + "\n")
    sels = [c for c in cands if c.idx > cfg.minimo_indice_para_publicar]
    banca = cfg.banca or site.read_credit()
    for c in sels:
        print(f"{'[SIM]' if cfg.simulacao else '[REAL]'} Under {c.line.ft_line_raw} @{c.line.ft_under} "
              f"em {c.key} ({c.partida.home} v {c.partida.away}), idx {c.idx:.4f}")
        base = {"home_v_away": c.key, "asianodds": f"{c.partida.home} v {c.partida.away}",
                "goalline": c.line.ft_line, "timestamp": time.time()}
        try:
            r = apostar(site, c, cfg, banca, est)
            print(f"   -> {'simulado' if r.get('simulado') else 'enviado'}: {r['valor']} @ {r['odds']}")
            est.published.append({**base, **r})
        except Exception as e:
            # marca mesmo assim para não repetir o jogo em loop (como no bot365_blogabet)
            est.published.append({**base, "odds": c.line.ft_under, "idx": c.idx, "valor": 0, "erro": str(e)})
            est.erro(str(e))
        est.save()
    est.save()


def main() -> None:
    cfg = Config.load()
    if not cfg.licenca or not cfg.usuario:
        raise SystemExit("Defina APOSTEME_LICENCA e APOSTEME_USUARIO no .env")
    print(f"Modo: {'SIMULAÇÃO' if cfg.simulacao else 'APOSTAS REAIS'} | casa {cfg.bookie} | idx mín {cfg.minimo_indice_para_publicar}")
    est = Estado(cfg.estado_arquivo)
    casador = Casador(minimo=cfg.jaro_minimo)
    site = AsianOddsSite(cfg)
    site.start()
    t_reload = time.time()
    try:
        while True:
            t0 = time.time()
            try:
                if site.is_logged_out() or site.feed_age_s() > 120 or time.time() - t_reload > 30 * 60:
                    print("Recarregando a página (sessão/feed)...")
                    site.reload()
                    t_reload = time.time()
                ciclo(site, cfg, est, casador)
            except Exception as e:
                est.erro(f"ciclo: {e}")
                traceback.print_exc()
                est.save()
            time.sleep(max(1.0, cfg.intervalo_seg - (time.time() - t0)))
    except KeyboardInterrupt:
        pass
    finally:
        site.stop()


if __name__ == "__main__":
    main()
