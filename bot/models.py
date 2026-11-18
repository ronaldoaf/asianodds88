"""Converte as mensagens EVF do feed ao vivo em objetos fáceis de usar.

Campos do EVF observados no site (nov/2026):
  LID      id da linha (tabela HTML id="id_<LID>"); cada linha de gols alternativa tem o seu
  MTCHID   id da partida (tabela tem a classe matchId_<MTCHID>); sufixo TTA/TTH = team totals
  HN/AN    mandante/visitante   LN liga   MT "Live"
  HS/AS    placar   RCH/RCA cartões vermelhos
  IGM      60 + minuto no 1º tempo, 120 + minuto no 2º tempo (ex.: 159 = 2T 39')
  EL       45 quando o relógio está correndo, 0 quando não há tempo informado
  FTGOAL   linha de gols do jogo (ex. "2.5" ou "2.5-3" = 2.75)
  FTOODDS  melhor odd Over   FTOUODDS melhor odd Under  (formato decimal "00")
  HTGOAL/HTOODD/HTUODD  idem para o 1º tempo
"""
from dataclasses import dataclass
from typing import Optional


def parse_line(s: str) -> Optional[float]:
    if not s:
        return None
    try:
        parts = [float(p) for p in str(s).split("-") if p != ""]
    except ValueError:
        return None
    return sum(parts) / len(parts) if parts else None


def parse_odd(s) -> Optional[float]:
    try:
        v = float(s)
        return v if v > 1.0 else None
    except (TypeError, ValueError):
        return None


def game_minute(igm, el) -> Optional[int]:
    try:
        igm = int(igm)
    except (TypeError, ValueError):
        return None
    if igm >= 120:
        return 45 + (igm - 120)
    if igm > 60 or (igm == 60 and el):
        return igm - 60
    return None  # "Live" sem relógio (intervalo/indefinido)


@dataclass
class Line:
    lid: int
    match_id: str
    league: str
    home: str
    away: str
    home_goals: int
    away_goals: int
    red_home: int
    red_away: int
    minute: Optional[int]
    ft_line: Optional[float]
    ft_line_raw: str
    ft_over: Optional[float]
    ft_under: Optional[float]

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    @property
    def is_main_market(self) -> bool:
        """Exclui team totals, escanteios, cartões etc."""
        name = f"{self.home} {self.away}".lower()
        if self.match_id.endswith(("TTA", "TTH")):
            return False
        return not any(w in name for w in ("corner", "booking", "team totals", "no. of"))

    @classmethod
    def from_evf(cls, e: dict) -> "Line":
        return cls(
            lid=int(e.get("LID")),
            match_id=str(e.get("MTCHID", "")),
            league=e.get("LN", ""),
            home=e.get("HN", ""),
            away=e.get("AN", ""),
            home_goals=int(e.get("HS") or 0),
            away_goals=int(e.get("AS") or 0),
            red_home=int(e.get("RCH") or 0),
            red_away=int(e.get("RCA") or 0),
            minute=game_minute(e.get("IGM"), e.get("EL")),
            ft_line=parse_line(e.get("FTGOAL", "")),
            ft_line_raw=e.get("FTGOAL", ""),
            ft_over=parse_odd(e.get("FTOODDS")),
            ft_under=parse_odd(e.get("FTOUODDS")),
        )
