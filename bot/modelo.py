"""Partes reutilizadas do bot365_blogabet: modelo ONNX, índice, stake, Jaro-Winkler e lucro da Goal Line."""
import math
import os
import re
import unicodedata
from pathlib import Path

import numpy as np
import onnxruntime as ort

_MODEL = Path(os.environ.get("MODELO_ONNX", Path(__file__).parent / "model.onnx"))
_session = None


def _sess():
    global _session
    if _session is None:
        if not _MODEL.exists():
            raise FileNotFoundError(f"Modelo não encontrado em {_MODEL}: copie o model.onnx do bot365_blogabet "
                                    "para bot/model.onnx ou defina MODELO_ONNX")
        _session = ort.InferenceSession(str(_MODEL), providers=["CPUExecutionProvider"])
    return _session


def calc_index(st: dict, goalline: float, odds_u: float) -> float:
    """Igual ao calcIndex: X=[s_g,s_s,s_c,d_g,oddsU,goal_diff,W,gl_0,i_da]."""
    g = {k: float(st.get(k) or 0) for k in ("gH", "gA", "cH", "cA", "daH", "daA", "sH", "sA", "W", "gl_0")}
    s_g = g["gH"] + g["gA"]
    s_da = g["daH"] + g["daA"]
    i_da = abs(g["daH"] - g["daA"]) / s_da if s_da > 0 else 0.0
    x = [s_g, g["sH"] + g["sA"], g["cH"] + g["cA"], abs(g["gH"] - g["gA"]), odds_u,
         goalline - s_g, g["W"], g["gl_0"], i_da]
    s = _sess()
    out = s.run(None, {s.get_inputs()[0].name: np.array([x], dtype=np.float32)})[0]
    return float(np.asarray(out).ravel()[0])


def perc_banca(idx: float, kelly: float, maximo: float) -> float:
    """Fração da banca: min(idx*kelly, maximo)."""
    return max(0.0, min(idx * kelly, maximo))


def stake_1a10(idx: float, kelly: float, maximo: float) -> int:
    perc = perc_banca(idx, kelly, maximo)
    return max(1, min(10, math.ceil(perc / maximo * 10)))


def p_over(odds_o: float, odds_u: float) -> float:
    return (1 / odds_o) / (1 / odds_o + 1 / odds_u)


def norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", t)


def jaro_winkler(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    l1, l2 = len(s1), len(s2)
    if not l1 or not l2:
        return 0.0
    dist = max(0, max(l1, l2) // 2 - 1)
    m1, m2 = [False] * l1, [False] * l2
    m = 0
    for i in range(l1):
        for j in range(max(0, i - dist), min(l2, i + dist + 1)):
            if m2[j] or s1[i] != s2[j]:
                continue
            m1[i] = m2[j] = True
            m += 1
            break
    if not m:
        return 0.0
    t = k = 0
    for i in range(l1):
        if not m1[i]:
            continue
        while not m2[k]:
            k += 1
        if s1[i] != s2[k]:
            t += 1
        k += 1
    jaro = (m / l1 + m / l2 + (m - t / 2) / m) / 3
    p = 0
    while p < 4 and p < min(l1, l2) and s1[p] == s2[p]:
        p += 1
    return jaro + p * 0.1 * (1 - jaro)


def lucro_goal_line(tipo: str, linha: float, gols: int, odds: float, stake: float) -> float:
    d = linha - gols if tipo == "Under" else gols - linha
    r = 1 if d >= 0.5 else 0.5 if d == 0.25 else 0 if d == 0 else -0.5 if d == -0.25 else -1
    return stake * (odds - 1) * r if r > 0 else stake * r
