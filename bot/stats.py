"""Stats dos jogos no intervalo, do servidor aposte.me (mesma fonte do bot365_blogabet)."""
import time
from typing import List

import requests

URL = "https://aposte.me/bot/stats.php"


def fetch_stats(licenca: str, usuario: str, max_idade_min: float) -> List[dict]:
    r = requests.post(URL, data="[]", headers={"licenca": licenca, "usuario": usuario}, timeout=20)
    r.raise_for_status()
    agora = time.time()
    return [st for st in r.json() if agora - float(st.get("ts") or 0) <= max_idade_min * 60]
