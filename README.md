# Bot AsianOdds88: Under no intervalo

Versão para a AsianOdds88 do `bot365_blogabet`: em vez de publicar a pick no Blogabet, **aposta o Under** pela interface do site
(conta do site, sem Web API). A estrutura do site está em [docs/estrutura-site.md](docs/estrutura-site.md).

## Ciclo (a cada `INTERVALO_SEG`)
1. Baixa as stats dos jogos no intervalo em `aposte.me/bot/stats.php` (descarta as com mais de `MAX_IDADE_STATS_MIN`).
2. Lê as linhas ao vivo da AsianOdds direto do feed da página (`bot/hook.js`): cada partida tem várias linhas de gols
   do jogo inteiro, com a melhor odd de Over e Under.
3. **Casa os nomes Bet365 → AsianOdds** (`bot/casamento.py`):
   - tabela `aliases.json` (`"nome bet365": "nome asianodds"`), que você pode editar e que o bot vai preenchendo sozinho;
   - comparação time a time, com nomes normalizados (sem acento, sem FC/CF/SC/Club..., abreviações como Utd/Atl/Man/St);
   - categoria precisa bater (feminino `(W)`, sub-xx, reservas);
   - média das notas ≥ `JARO_MINIMO`, pior nota ≥ 0.75, e vantagem clara sobre a 2ª opção;
   - placar igual ao das stats;
   - casos em dúvida vão para `pendentes.json` com as 3 melhores sugestões.
4. Regras do spec: sem cartão vermelho, já publicado nas últimas 24 h, linha equilibrada (`|p_over − 0.5| < MAX_DESEQUILIBRIO_ODDS`),
   `oddsU ≥ ODDS_MINIMA`, maior índice do modelo ONNX, `idx > MINIMO_INDICE`. Extra: não entra se a AsianOdds já mostra o jogo
   depois de `MAX_MINUTO_AO`.
5. Abre o cupom, relê a odd da casa (`AO_BOOKIE`, padrão Pinnacle), confere a linha, **recalcula o índice** se a odd mudou e
   cancela se não passar. Valor = `min(idx × KELLY, MAX) × banca` (banca = `BANCA` ou o "Credit" do site), respeitando o mínimo/máximo
   da casa e `EXPOSICAO_MAX_DIA`. A odd mínima aceita no cupom é a própria odd lida (não aceita pior).
6. Em simulação (`SIMULACAO=true`, padrão) só registra. Tudo vai para `estado.json` (`published`, `errors`, `ultimo_ciclo` com candidatos e descartes).
   Falhas também são registradas para não repetir o jogo.

## Uso
```bash
pip install -r requirements.txt
playwright install chromium
cp ../bot365_blogabet/model.onnx bot/model.onnx   # o modelo não vai para este repo (é público)
cp .env.example .env                              # preencha AO_*, APOSTEME_*
python -m bot.main
```

## Pontos de atenção
- O modelo foi treinado com odds da Bet365; as da Pinnacle tendem a ser maiores e inflar o índice. Rode em simulação e
  revise `MINIMO_INDICE` antes de apostar.
- A odd usada na triagem é a melhor entre todas as casas da AsianOdds; a decisão final usa a odd da `AO_BOOKIE` no cupom.
- A confirmação depois de "Place Bet" ainda não foi testada com uma aposta real.
- Os termos da AsianOdds88 não proíbem bots explicitamente, mas a conta pode ser limitada a qualquer momento.
