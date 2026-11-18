# Bot AsianOdds88: Under ao vivo

Bot em Python + Playwright que usa a **interface do site** (não a Web API) para apostar em Under em jogos de futebol ao vivo.
A estrutura do site está em [docs/estrutura-site.md](docs/estrutura-site.md).

## Como funciona
1. Abre um Chromium com perfil próprio (`perfil-chrome/`), faz login (automático com `AO_USER`/`AO_PASS`, ou manual) e deixa só o filtro **Live**.
2. Um script injetado (`bot/hook.js`) copia as mensagens do feed ao vivo (`EVF`) para `window.__aoBot`.
3. A cada `AO_POLL_SECONDS`, `bot/strategy.py` escolhe as linhas de Under que batem com a regra.
4. Para cada uma, clica no Under da grade, lê o cupom (casas, odd, limites) e:
   - em **simulação** (`AO_DRY_RUN=true`, padrão) só registra e fecha o cupom;
   - em modo real preenche valor e odd mínima, clica em *Place Bet* e confirma.
5. Tudo vai para `apostas.csv`.

## Uso
```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # ajuste a estratégia
python -m bot.main     # começa em simulação
```

## Estratégia
A regra em `bot/strategy.py` é só um exemplo (minuto 60–80, até 2 gols, linha ≥ gols + 1, odd ≥ 1.80). Troque pela sua.

## Cuidados
- Os termos da AsianOdds88 não proíbem bots explicitamente, mas a conta pode ser limitada/fechada a qualquer momento.
- Uma aposta só vale com ID de transação em "My Bets". Confira as primeiras apostas reais manualmente.
- Rode sempre primeiro em simulação.
