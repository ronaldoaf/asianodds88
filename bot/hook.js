// Injetado em toda página do site (Playwright add_init_script).
// Embrulha a função global processMarketSocketMessage do site para guardar
// as mensagens do feed ao vivo em window.__aoBot, sem alterar o comportamento.
(() => {
  if (window.__aoBot) return;
  const bot = (window.__aoBot = {
    events: {},   // LID -> último EVF (uma linha de mercado por LID)
    removed: {},  // LID removidos (RemoveLocalID)
    other: [],    // outras mensagens (tickets, placement data etc.), últimas 300
    lastMsgAt: 0,
    hooked: false,
  });
  function handle(raw) {
    let o;
    try { o = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (e) { return; }
    if (!o || typeof o !== 'object') return;
    bot.lastMsgAt = Date.now();
    if (o.EVF) {
      const prev = bot.events[o.EVF.LID] || {};
      bot.events[o.EVF.LID] = Object.assign(prev, o.EVF, { _ts: Date.now() });
      delete bot.removed[o.EVF.LID];
      return;
    }
    if (o.RID !== undefined && o.MID !== undefined && Object.keys(o).length <= 3) {
      bot.removed[o.RID] = Date.now();
      delete bot.events[o.RID];
      return;
    }
    if (o.Code !== undefined && o.Message === 'Pong') return;
    bot.other.push({ ts: Date.now(), msg: o });
    if (bot.other.length > 300) bot.other.shift();
  }
  function tryHook() {
    if (bot.hooked) return true;
    const fn = window.processMarketSocketMessage;
    if (typeof fn !== 'function') return false;
    window.processMarketSocketMessage = function (...args) {
      try { handle(args[0]); } catch (e) {}
      return fn.apply(this, args);
    };
    bot.hooked = true;
    return true;
  }
  document.addEventListener('DOMContentLoaded', tryHook);
  const t = setInterval(() => { if (tryHook()) clearInterval(t); }, 20);
})();
