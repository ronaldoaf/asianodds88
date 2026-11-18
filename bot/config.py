"""Configuração lida de variáveis de ambiente (ou de um arquivo .env).

Os nomes seguem o config do bot365_blogabet (js/shared.js)."""
import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split(" #")[0].strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _get(name, default, cast):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    if cast is bool:
        return v.strip().lower() in ("1", "true", "sim", "yes")
    return cast(v)


@dataclass
class Config:
    # site
    user: str = ""
    password: str = ""
    profile_dir: str = "perfil-chrome"
    headless: bool = False
    bookie: str = "PIN"                 # casa usada no cupom (na conta só a Pinnacle está ativa)

    # fonte de stats (aposte.me)
    licenca: str = ""
    usuario: str = ""

    # estratégia (mesmos nomes/padrões do bot365_blogabet)
    simulacao: bool = True
    minimo_indice_para_publicar: float = 0.12   # análise: 0.12–0.13
    percentual_de_kelly: float = 0.4
    maximo_da_banca_por_aposta: float = 0.1
    odds_minima: float = 1.825
    max_desequilibrio_odds: float = 0.075
    max_idade_stats_min: float = 6
    intervalo_seg: float = 30
    jaro_minimo: float = 0.9            # nota mínima do casamento de nomes Bet365 x AsianOdds
    max_minuto_ao: int = 55             # não entra se a AsianOdds já mostra o jogo além deste minuto

    # dinheiro (novos, para apostar de verdade)
    banca: float = 0.0                  # 0 = usa o "Credit" mostrado no site
    exposicao_max_dia: float = 0.0      # 0 = sem limite; soma dos valores apostados no dia
    estado_arquivo: str = "estado.json"

    @classmethod
    def load(cls) -> "Config":
        _load_dotenv()
        d = cls()
        env = {
            "user": ("AO_USER", str), "password": ("AO_PASS", str), "profile_dir": ("AO_PROFILE_DIR", str),
            "headless": ("AO_HEADLESS", bool), "bookie": ("AO_BOOKIE", str),
            "licenca": ("APOSTEME_LICENCA", str), "usuario": ("APOSTEME_USUARIO", str),
            "simulacao": ("SIMULACAO", bool),
            "minimo_indice_para_publicar": ("MINIMO_INDICE", float),
            "percentual_de_kelly": ("PERCENTUAL_DE_KELLY", float),
            "maximo_da_banca_por_aposta": ("MAXIMO_DA_BANCA_POR_APOSTA", float),
            "odds_minima": ("ODDS_MINIMA", float),
            "max_desequilibrio_odds": ("MAX_DESEQUILIBRIO_ODDS", float),
            "max_idade_stats_min": ("MAX_IDADE_STATS_MIN", float),
            "intervalo_seg": ("INTERVALO_SEG", float),
            "jaro_minimo": ("JARO_MINIMO", float), "max_minuto_ao": ("MAX_MINUTO_AO", int),
            "banca": ("BANCA", float), "exposicao_max_dia": ("EXPOSICAO_MAX_DIA", float),
            "estado_arquivo": ("ESTADO_ARQUIVO", str),
        }
        for attr, (name, cast) in env.items():
            setattr(d, attr, _get(name, getattr(d, attr), cast))
        d.bookie = d.bookie.upper()
        return d
