"""Regras de decisão do bot365_blogabet (§5 do spec), usando as linhas ao vivo da AsianOdds."""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import Config
from .casamento import Casador
from .modelo import calc_index, p_over
from .models import Line


@dataclass
class Partida:
    match_id: str
    home: str
    away: str
    league: str
    home_goals: int
    away_goals: int
    red: int
    minute: Optional[int]
    lines: List[Line] = field(default_factory=list)


@dataclass
class Candidato:
    key: str
    st: dict
    partida: Partida
    line: Line
    idx: float
    opcoes: List = field(default_factory=list)  # [(idx_feed, Line)] de todas as linhas válidas, melhor primeiro


def agrupar(lines: List[Line]) -> List[Partida]:
    """Junta as linhas (LIDs) de cada partida; ignora team totals, escanteios etc."""
    por = defaultdict(list)
    for ln in lines:
        if ln.is_main_market:
            por[ln.match_id].append(ln)
    out = []
    for mid, ls in por.items():
        a = max(ls, key=lambda l: (l.home_goals + l.away_goals))  # placar mais recente
        out.append(Partida(mid, a.home, a.away, a.league, a.home_goals, a.away_goals,
                           a.red_home + a.red_away, a.minute, ls))
    return out


def avaliar(stats: List[dict], lines: List[Line], cfg: Config, ja: set, casador: Casador):
    partidas = agrupar(lines)
    descartes: Dict[str, list] = {k: [] for k in
        ("ja_publicado", "cartao_vermelho", "minuto_alto", "sem_evento", "placar_diferente", "sem_goal_line", "sem_linha_valida")}
    candidatos: List[Candidato] = []
    for st in stats:
        key = f"{st.get('home')} v {st.get('away')}"
        if key in ja:
            descartes["ja_publicado"].append(key); continue
        if int(float(st.get("rh") or 0)) + int(float(st.get("ra") or 0)) > 0:
            descartes["cartao_vermelho"].append(key); continue
        p, motivo = casador.casar(st, partidas)
        if not p:
            descartes[motivo].append(key); continue
        if p.red > 0:
            descartes["cartao_vermelho"].append(key); continue
        if p.minute is not None and p.minute > cfg.max_minuto_ao:
            descartes["minuto_alto"].append(key); continue
        ls = [l for l in p.lines if l.ft_line is not None and l.ft_over and l.ft_under]
        if not ls:
            descartes["sem_goal_line"].append(key); continue
        best = None
        opcoes = []
        for l in ls:
            if abs(p_over(l.ft_over, l.ft_under) - 0.5) >= cfg.max_desequilibrio_odds:
                continue
            if l.ft_under < cfg.odds_minima:
                continue
            idx = calc_index(st, l.ft_line, l.ft_under)
            opcoes.append((idx, l))
            if best is None or idx > best.idx:
                best = Candidato(key, st, p, l, idx)
        if best is None:
            descartes["sem_linha_valida"].append(key); continue
        best.opcoes = sorted(opcoes, key=lambda x: x[0], reverse=True)
        candidatos.append(best)
    return candidatos, descartes
