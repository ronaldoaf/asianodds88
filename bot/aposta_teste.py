"""Aposta de teste manual: você escolhe o jogo e confirma no terminal.

Uso:
  python -m bot.aposta_teste "San Juan"            # mostra o cupom e NÃO aposta
  python -m bot.aposta_teste "San Juan" --apostar   # pede confirmação digitada e aposta o mínimo da casa
Opções: --linha 4.25  (padrão: maior linha de gols da partida)   --valor 5  (padrão: mínimo da casa)
"""
import argparse
import json
import time

from .config import Config
from .site import AsianOddsSite


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jogo", help="parte do nome de um dos times, como aparece na AsianOdds")
    ap.add_argument("--linha", type=float, default=None)
    ap.add_argument("--valor", type=float, default=None)
    ap.add_argument("--apostar", action="store_true")
    a = ap.parse_args()

    cfg = Config.load()
    cfg.simulacao = True  # só libera depois da confirmação digitada
    site = AsianOddsSite(cfg)
    site.start()
    try:
        time.sleep(5)  # deixa o feed encher
        alvo = a.jogo.lower()
        ls = [l for l in site.live_lines() if l.is_main_market and l.ft_line is not None and l.ft_under
              and (alvo in l.home.lower() or alvo in l.away.lower()) and site.line_on_screen(l.lid)]
        if not ls:
            print("Jogo/linha não encontrado na grade Live.")
            return
        if a.linha is not None:
            ls = [l for l in ls if abs(l.ft_line - a.linha) < 1e-6] or ls
        ln = max(ls, key=lambda l: l.ft_line) if a.linha is None else ls[0]
        print(f"Jogo: {ln.home} x {ln.away} ({ln.home_goals}-{ln.away_goals}, {ln.minute}') | Under {ln.ft_line_raw} @ {ln.ft_under}")
        slip = site.open_under_slip(ln.lid)
        print("Cupom:", json.dumps(slip, ensure_ascii=False, indent=1))
        book = next((b for b in (slip or {}).get("books", []) if b["code"] == cfg.bookie and b["checked"] and b["price"]), None)
        if not book:
            print(f"{cfg.bookie} sem preço no cupom.")
            site.close_slip()
            return
        valor = a.valor or book["min"]
        if not a.apostar:
            print(f"(teste sem aposta) apostaria {valor} @ {book['price']} na {cfg.bookie}. Use --apostar para apostar.")
            site.close_slip()
            return
        resp = input(f"Apostar {valor} no Under {book['line']} @ {book['price']} ({cfg.bookie})? Digite SIM: ")
        if resp.strip().upper() != "SIM":
            print("Cancelado.")
            site.close_slip()
            return
        cfg.simulacao = False
        r = site.place_open_slip(valor, book["price"])
        print("Erro no cupom:", r["error"] or "(nenhum)")
        print("Mensagens do site depois do envio:")
        for m in r["messages"]:
            print(json.dumps(m["msg"], ensure_ascii=False)[:600])
        site.close_slip()
        print("Confira em Pending Bets / My Bets se apareceu o ID da transação.")
        input("Enter para fechar o navegador...")
    finally:
        site.stop()


if __name__ == "__main__":
    main()
