"""Regra de entrada no Under. É um EXEMPLO: troque pela sua estratégia."""
from typing import Iterable, List

from .config import Config
from .models import Line


def pick_unders(lines: Iterable[Line], cfg: Config) -> List[Line]:
    """Devolve no máximo uma linha por partida que atende à regra."""
    best = {}
    for ln in lines:
        if not ln.is_main_market or ln.minute is None or ln.ft_line is None or ln.ft_under is None:
            continue
        if ln.league.upper() in cfg.leagues_block:
            continue
        if not (cfg.min_minute <= ln.minute <= cfg.max_minute):
            continue
        if ln.total_goals > cfg.max_total_goals:
            continue
        if ln.ft_line - ln.total_goals < cfg.min_line_margin:
            continue
        if ln.ft_under < cfg.min_under_odd:
            continue
        cur = best.get(ln.match_id)
        # prefere a linha mais alta (mais folga), depois a melhor odd
        if cur is None or (ln.ft_line, ln.ft_under) > (cur.ft_line, cur.ft_under):
            best[ln.match_id] = ln
    return list(best.values())
