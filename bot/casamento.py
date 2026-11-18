"""Associa os jogos das stats (nomes da Bet365) às partidas da AsianOdds.

Estratégia, em ordem:
1. Tabela de apelidos (aliases.json): "nome bet365" -> "nome asianodds", editável à mão.
   O bot também aprende sozinho: todo casamento com confiança alta grava os dois times.
2. Comparação time a time (mandante com mandante, visitante com visitante), depois de
   normalizar: minúsculas, sem acento, sem termos genéricos (FC, CF, SC, Club, Deportivo...),
   e com marcadores de categoria padronizados (Women/(W)/Fem -> w, U21/Sub-21 -> u21,
   Reserves/II/B -> res). A nota de cada time é o máximo entre Jaro-Winkler e a sobreposição de palavras.
3. Categoria tem que bater: um time feminino/sub-xx/reserva só casa com a mesma categoria.
4. O placar tem que ser igual ao das stats (filtra homônimos e jogos errados).
5. Aceita se a média das duas notas >= jaro_minimo e a pior nota >= 0.75, e se a melhor
   partida está claramente acima da segunda (margem 0.03). Casos em dúvida vão para
   pendentes.json com as 3 melhores sugestões, para você confirmar em aliases.json.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .modelo import jaro_winkler, norm

GENERICOS = {
    "fc", "cf", "sc", "ac", "afc", "cd", "ca", "club", "clube", "deportivo", "deportiva",
    "fk", "sk", "nk", "if", "bk", "ff", "sv", "vfb", "vfl", "tsv", "fsv", "ss", "us", "as", "asd",
    "calcio", "cp", "ud", "rcd", "sd", "cs", "csd", "ad", "ec", "se", "esporte", "futebol", "football",
    "soccer", "the", "de", "del", "la", "el", "da", "do", "dos", "das",
}
ABREVIACOES = {
    "utd": "united", "atl": "atletico", "atletico": "atletico", "man": "manchester", "st": "saint",
    "dep": "deportivo", "int": "internacional", "inter": "inter", "muenchen": "munich", "munchen": "munich",
    "wolves": "wolverhampton", "spurs": "tottenham", "psg": "paris saint germain",
}
CATEGORIAS = [
    (r"\(w\)|\bwomen\b|\bwomens\b|\bladies\b|\bfem(enino|enina|inine)?\b|\bfeminino\b", "w"),
    (r"\bu-?(\d{2})\b|\bsub-?(\d{2})\b|\bunder ?(\d{2})\b", "u"),
    (r"\breserves?\b|\bres\.?\b|\bii\b|\b2\b|\bb\b", "res"),
]


def _ascii(t: str) -> str:
    return norm(t) and re.sub(r"\s+", " ", re.sub(r"[^a-z0-9() ]", " ", _strip(t.lower()))).strip()


def _strip(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def analisa(nome: str) -> Tuple[str, frozenset, str]:
    """-> (texto normalizado sem espaços, conjunto de palavras, categoria)."""
    t = _ascii(nome)
    cat = ""
    for pat, tag in CATEGORIAS:
        m = re.search(pat, t)
        if m:
            if tag == "u":
                cat = "u" + next(g for g in m.groups() if g)
            elif not cat:
                cat = tag
            t = re.sub(pat, " ", t)
    brutas = " ".join(ABREVIACOES.get(w, w) for w in re.sub(r"[()]", " ", t).split()).split()
    palavras = [w for w in brutas if w and w not in GENERICOS]
    if not palavras:  # nome só com termos genéricos: usa o original
        palavras = brutas
    return "".join(palavras), frozenset(palavras), cat


def _palavra_casa(w: str, outras) -> bool:
    for o in outras:
        if w == o or (min(len(w), len(o)) >= 3 and (o.startswith(w) or w.startswith(o))):
            return True
        if min(len(w), len(o)) >= 5 and jaro_winkler(w, o) >= 0.92:
            return True
    return False


def nota_time(a: str, b: str) -> float:
    """0..1. Com várias palavras, todas as palavras do nome mais curto precisam aparecer no outro
    (por isso "Manchester City" x "Manchester United" dá 0.5); com uma palavra de cada lado usa Jaro-Winkler."""
    ta, wa, ca = analisa(a)
    tb, wb, cb = analisa(b)
    if ca != cb or not ta or not tb:
        return 0.0
    if ta == tb:
        return 1.0
    curto, longo = (wa, wb) if len(wa) <= len(wb) else (wb, wa)
    if len(wa) == 1 and len(wb) == 1:
        return jaro_winkler(ta, tb)
    frac = sum(_palavra_casa(w, longo) for w in curto) / len(curto)
    jw = jaro_winkler(ta, tb)
    return max(frac, jw if jw >= 0.95 else 0.0)


class Casador:
    def __init__(self, aliases_path="aliases.json", pendentes_path="pendentes.json",
                 minimo=0.9, pior_minima=0.75, margem=0.03):
        self.aliases_path, self.pendentes_path = Path(aliases_path), Path(pendentes_path)
        self.minimo, self.pior_minima, self.margem = minimo, pior_minima, margem
        self.aliases: Dict[str, str] = {}
        if self.aliases_path.exists():
            self.aliases = json.loads(self.aliases_path.read_text(encoding="utf-8"))

    def _alias(self, nome: str) -> str:
        return self.aliases.get(nome, nome)

    def _aprende(self, b365: str, ao: str) -> None:
        if b365 != ao and self.aliases.get(b365) != ao:
            self.aliases[b365] = ao
            self.aliases_path.write_text(json.dumps(self.aliases, ensure_ascii=False, indent=1, sort_keys=True),
                                         encoding="utf-8")

    def _pendente(self, st: dict, sugestoes: list) -> None:
        pend = {}
        if self.pendentes_path.exists():
            try:
                pend = json.loads(self.pendentes_path.read_text(encoding="utf-8"))
            except ValueError:
                pend = {}
        pend[f"{st.get('home')} v {st.get('away')}"] = sugestoes
        self.pendentes_path.write_text(json.dumps(pend, ensure_ascii=False, indent=1), encoding="utf-8")

    def casar(self, st: dict, partidas: List, exige_placar: bool = True):
        """partidas: objetos com .home .away .home_goals .away_goals. Devolve (partida|None, motivo)."""
        h, a = str(st.get("home", "")), str(st.get("away", ""))
        gh, ga = int(float(st.get("gH") or 0)), int(float(st.get("gA") or 0))
        ah, aa = self._alias(h), self._alias(a)
        notas = []
        for p in partidas:
            if ah == p.home and aa == p.away:
                n1 = n2 = 1.0
            else:
                n1, n2 = nota_time(ah, p.home), nota_time(aa, p.away)
            notas.append(((n1 + n2) / 2, min(n1, n2), p))
        notas.sort(key=lambda x: x[0], reverse=True)
        if not notas or notas[0][0] < 0.6:
            return None, "sem_evento"
        media, pior, p = notas[0]
        segunda = notas[1][0] if len(notas) > 1 else 0.0
        placar_ok = (p.home_goals, p.away_goals) == (gh, ga)
        if media >= self.minimo and pior >= self.pior_minima and media - segunda >= self.margem:
            if exige_placar and not placar_ok:
                return None, "placar_diferente"
            self._aprende(h, p.home)
            self._aprende(a, p.away)
            return p, "ok"
        self._pendente(st, [{"home": x[2].home, "away": x[2].away, "nota": round(x[0], 3),
                             "placar": f"{x[2].home_goals}-{x[2].away_goals}"} for x in notas[:3]])
        return None, "sem_evento"
