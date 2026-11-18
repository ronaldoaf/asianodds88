"""Controle do site bet.asianodds88.com via Playwright.

Mapa da interface (nov/2026):
  Login:   https://bet.asianodds88.com/login.html  -> #txtUserID, #txtPass, #btnDoLogin
           depois redireciona para https://appNNN.asianodds88.com/UserPages/market.html
  Filtros: checkboxes "Live" / "Today" / "Early" no topo da grade
  Grade:   cada linha de mercado é <table class="igametable matchId_<MTCHID>" id="id_<LID>">
           odds clicáveis: span.FTOver / span.FTUnder / span.HTOver / span.HTUnder (classe BetItem)
           clicar chama clickBetItem(this,'f','o','a','FTGoal') e abre o cupom
  Cupom:   jQuery UI dialog #dlgPlaceBet
           uma tabela por casa: table.iUserDataItem#ibookie<COD> (PIN, SBO, SIN, 3ET...)
             input.isCheckedForBet (casa marcada), span.spanPrice (odd), span.spanMinAmount/spanMaxAmount
             input.hiddRealMinAmount / input.hiddRealMaxAmount (limites numéricos), input.hiddHDPorGoal (linha)
           #betdlg_USR_AMOUNT (valor), #betdlg_minimumprice (odd mínima aceita),
           #btnDlgPlaceBetSubmit (Place Bet), #dlgPlaceBetClose (fechar)
           Depois do Place Bet pode aparecer um diálogo de confirmação com button.btnYes
           (a opção "Place Bet Without Confirmation" fica em Settings).
"""
import time
from pathlib import Path
from typing import Dict, List, Optional

from playwright.sync_api import BrowserContext, Page, sync_playwright

from .config import Config
from .models import Line

LOGIN_URL = "https://bet.asianodds88.com/login.html"
HOOK_JS = (Path(__file__).parent / "hook.js").read_text(encoding="utf-8")


class AsianOddsSite:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._pw = None
        self.ctx: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    # ---------- sessão ----------
    def start(self) -> None:
        self._pw = sync_playwright().start()
        self.ctx = self._pw.chromium.launch_persistent_context(
            self.cfg.profile_dir, headless=self.cfg.headless, viewport={"width": 1500, "height": 900}
        )
        self.ctx.add_init_script(HOOK_JS)
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.ensure_logged_in()

    def stop(self) -> None:
        if self.ctx:
            self.ctx.close()
        if self._pw:
            self._pw.stop()

    def ensure_logged_in(self, wait_manual_s: int = 300) -> None:
        p = self.page
        if "/UserPages/market.html" not in p.url:
            p.goto(LOGIN_URL, wait_until="domcontentloaded")
            p.wait_for_timeout(2000)
        if "/UserPages/market.html" in p.url:
            self._wait_market()
            return
        if self.cfg.user and self.cfg.password:
            p.fill("#txtUserID", self.cfg.user)
            p.fill("#txtPass", self.cfg.password)
            p.click("#btnDoLogin")
        else:
            print(f"Faça o login manualmente na janela do navegador (até {wait_manual_s}s)...")
        p.wait_for_url("**/UserPages/market.html*", timeout=wait_manual_s * 1000)
        self._wait_market()

    def _wait_market(self) -> None:
        p = self.page
        p.wait_for_selector("table.igametable", timeout=60000)
        p.wait_for_function("window.__aoBot && window.__aoBot.hooked", timeout=30000)
        self.only_live()

    def only_live(self) -> None:
        """Deixa só o filtro Live marcado."""
        for label in ("Live", "Today", "Early"):
            want = label == "Live"
            self.page.evaluate(
                """([label, want]) => {
                    const cb = [...document.querySelectorAll('input[type=checkbox]')]
                      .find(e => e.labels && [...e.labels].some(l => l.innerText.trim() === label));
                    if (cb && cb.checked !== want) cb.click();
                }""",
                [label, want],
            )

    def is_logged_out(self) -> bool:
        return bool(self.page.evaluate(
            """() => [...document.querySelectorAll('.ui-dialog')].some(d =>
                d.offsetParent !== null && /Logged Out|Connection Error/i.test(d.innerText))"""
        )) or "login" in self.page.url

    # ---------- feed ----------
    def feed_age_s(self) -> float:
        last = self.page.evaluate("window.__aoBot ? window.__aoBot.lastMsgAt : 0")
        return (time.time() * 1000 - last) / 1000 if last else 1e9

    def live_lines(self) -> List[Line]:
        evs: Dict[str, dict] = self.page.evaluate("window.__aoBot ? window.__aoBot.events : {}")
        out = []
        for e in evs.values():
            if e.get("MT") != "Live":
                continue
            try:
                out.append(Line.from_evf(e))
            except Exception:
                continue
        return out

    def line_on_screen(self, lid: int) -> bool:
        return self.page.locator(f"table#id_{lid} span.FTUnder.BetItem").count() > 0

    def other_messages_since(self, ts_ms: float) -> list:
        return self.page.evaluate("(t) => window.__aoBot.other.filter(m => m.ts >= t)", ts_ms)

    # ---------- cupom ----------
    def open_under_slip(self, lid: int) -> Optional[dict]:
        """Clica no Under FT da linha e lê o cupom. Devolve as casas disponíveis."""
        p = self.page
        self.close_slip()
        span = p.locator(f"table#id_{lid} span.FTUnder.BetItem").first
        if span.count() == 0 or not span.inner_text().strip():
            return None
        span.scroll_into_view_if_needed()
        span.click()
        p.wait_for_selector("#dlgPlaceBet", state="visible", timeout=10000)
        # espera a(s) casa(s) responderem com preço
        p.wait_for_function(
            """() => [...document.querySelectorAll('#dlgPlaceBet table.iUserDataItem')]
                   .some(t => t.offsetParent !== null && /\\d/.test((t.querySelector('.spanPrice')||{}).innerText||''))""",
            timeout=15000,
        )
        return p.evaluate(
            """() => {
              const d = document.querySelector('#dlgPlaceBet');
              const books = [...d.querySelectorAll('table.iUserDataItem')].filter(t => t.offsetParent !== null).map(t => ({
                code: (t.querySelector('.spanMarket')||{}).innerText || t.id.replace('ibookie',''),
                checked: !!(t.querySelector('input.isCheckedForBet')||{}).checked,
                price: parseFloat((t.querySelector('.spanPrice')||{}).innerText) || null,
                min: parseFloat((t.querySelector('.hiddRealMinAmount')||{}).value) || null,
                max: parseFloat((t.querySelector('.hiddRealMaxAmount')||{}).value) || null,
                line: (t.querySelector('.hiddHDPorGoal')||{}).value || null,
              }));
              return {
                caption: (document.querySelector('#bedlg_info_caption')||{}).innerText,
                score: (document.querySelector('#betdlg_ScoreOrStartTime')||{}).innerText,
                teams: (document.querySelector('#betdlg_teams')||{}).innerText,
                average: parseFloat((document.querySelector('#betdlg_average')||{}).innerText) || null,
                books,
              };
            }"""
        )

    def close_slip(self) -> None:
        self.page.evaluate(
            "() => { const b = document.querySelector('#dlgPlaceBetClose'); "
            "if (b && document.querySelector('#dlgPlaceBet').offsetParent !== null) b.click(); }"
        )

    def place_open_slip(self, amount: float, min_odd: float) -> dict:
        """Preenche e envia o cupom aberto. Só chame com cfg.dry_run == False."""
        assert not self.cfg.dry_run, "dry_run ativo: aposta real bloqueada"
        p = self.page
        t0 = time.time() * 1000
        p.fill("#betdlg_USR_AMOUNT", f"{amount:.2f}".rstrip("0").rstrip("."))
        p.fill("#betdlg_minimumprice", f"{min_odd:.3f}")
        p.click("#btnDlgPlaceBetSubmit")
        # diálogo de confirmação (se não estiver desativado em Settings)
        try:
            yes = p.locator(".ui-dialog:visible button.btnYes").first
            yes.wait_for(state="visible", timeout=3000)
            yes.click()
        except Exception:
            pass
        p.wait_for_timeout(8000)
        err = p.evaluate("() => (document.querySelector('#betdlg_inerror')||{}).innerText || ''")
        return {"error": err.strip(), "messages": self.other_messages_since(t0)}
