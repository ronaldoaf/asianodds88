"""Configuração lida de variáveis de ambiente (ou de um arquivo .env)."""
import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _f(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _i(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _b(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "sim", "yes")


@dataclass
class Config:
    user: str = ""
    password: str = ""
    profile_dir: str = "perfil-chrome"
    headless: bool = False
    dry_run: bool = True            # True = só simula, nunca clica em "Place Bet"
    poll_seconds: float = 2.0

    # Estratégia (exemplo, ajuste à sua)
    min_minute: int = 60
    max_minute: int = 80
    max_total_goals: int = 2
    min_line_margin: float = 1.0    # linha de gols - gols marcados
    min_under_odd: float = 1.80
    stake: float = 5.0              # valor por aposta (moeda da conta)
    max_bets_per_match: int = 1
    max_bets_per_day: int = 10
    leagues_block: list = field(default_factory=list)

    @classmethod
    def load(cls) -> "Config":
        _load_dotenv()
        return cls(
            user=os.environ.get("AO_USER", ""),
            password=os.environ.get("AO_PASS", ""),
            profile_dir=os.environ.get("AO_PROFILE_DIR", "perfil-chrome"),
            headless=_b("AO_HEADLESS", False),
            dry_run=_b("AO_DRY_RUN", True),
            poll_seconds=_f("AO_POLL_SECONDS", 2.0),
            min_minute=_i("AO_MIN_MINUTE", 60),
            max_minute=_i("AO_MAX_MINUTE", 80),
            max_total_goals=_i("AO_MAX_TOTAL_GOALS", 2),
            min_line_margin=_f("AO_MIN_LINE_MARGIN", 1.0),
            min_under_odd=_f("AO_MIN_UNDER_ODD", 1.80),
            stake=_f("AO_STAKE", 5.0),
            max_bets_per_match=_i("AO_MAX_BETS_PER_MATCH", 1),
            max_bets_per_day=_i("AO_MAX_BETS_PER_DAY", 10),
            leagues_block=[s.strip().upper() for s in os.environ.get("AO_LEAGUES_BLOCK", "").split(",") if s.strip()],
        )
