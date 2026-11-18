"""Loop principal: lê o feed ao vivo, aplica a estratégia e aposta no Under.

Uso:  python -m bot.main          (simulação, padrão)
      AO_DRY_RUN=false python -m bot.main   (apostas reais)
"""
import csv
import datetime as dt
import time
from collections import Counter
from pathlib import Path

from .config import Config
from .site import AsianOddsSite
from .strategy import pick_unders

LOG = Path("apostas.csv")


def log_row(row: dict) -> None:
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    cfg = Config.load()
    print(f"Modo: {'SIMULAÇÃO' if cfg.dry_run else 'APOSTAS REAIS'} | stake {cfg.stake} | odd mín {cfg.min_under_odd}")
    site = AsianOddsSite(cfg)
    site.start()
    per_match: Counter = Counter()
    today = dt.date.today()
    bets_today = 0
    try:
        while True:
            if dt.date.today() != today:
                today, bets_today = dt.date.today(), 0
            if site.is_logged_out() or site.feed_age_s() > 120:
                print("Sessão caiu ou feed parado; recarregando...")
                site.page.reload()
                site.ensure_logged_in()

            for ln in pick_unders(site.live_lines(), cfg):
                if per_match[ln.match_id] >= cfg.max_bets_per_match or bets_today >= cfg.max_bets_per_day:
                    continue
                if not site.line_on_screen(ln.lid):
                    continue
                slip = site.open_under_slip(ln.lid)
                if not slip:
                    continue
                books = [b for b in slip["books"] if b["checked"] and b["price"]]
                price = max((b["price"] for b in books), default=None)
                desc = f"{ln.home} x {ln.away} {ln.home_goals}-{ln.away_goals} {ln.minute}' U{ln.ft_line_raw} @ {price}"
                row = {
                    "quando": dt.datetime.now().isoformat(timespec="seconds"), "liga": ln.league,
                    "jogo": f"{ln.home} x {ln.away}", "placar": f"{ln.home_goals}-{ln.away_goals}",
                    "minuto": ln.minute, "linha": ln.ft_line_raw, "odd": price, "stake": cfg.stake,
                    "casas": ",".join(b["code"] for b in books), "modo": "sim" if cfg.dry_run else "real",
                    "resultado": "",
                }
                if price is None or price < cfg.min_under_odd:
                    site.close_slip()
                    continue
                if not any((b["min"] or 0) <= cfg.stake <= (b["max"] or 1e12) for b in books):
                    print("Stake fora dos limites:", desc)
                    site.close_slip()
                    continue
                if cfg.dry_run:
                    print("[SIM] apostaria:", desc)
                    site.close_slip()
                    row["resultado"] = "simulado"
                else:
                    print("[REAL] apostando:", desc)
                    res = site.place_open_slip(cfg.stake, cfg.min_under_odd)
                    row["resultado"] = res["error"] or f"enviado ({len(res['messages'])} msgs)"
                    print("   ->", row["resultado"])
                    site.close_slip()
                    bets_today += 1
                per_match[ln.match_id] += 1
                log_row(row)
            time.sleep(cfg.poll_seconds)
    except KeyboardInterrupt:
        pass
    finally:
        site.stop()


if __name__ == "__main__":
    main()
