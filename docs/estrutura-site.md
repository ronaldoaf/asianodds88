# Estrutura do site AsianOdds88 (mapeada em 17/11/2026)

## Termos de uso
Os Termos e Condições (https://www.asianodds88.com/terms-conditions) não proíbem automação de forma explícita.
Porém a AsianOdds pode limitar ou encerrar o acesso "por qualquer motivo" (item 6), valem também os termos da
Asianconnect N.V. e de cada casa (Pinnacle, SBO, Singbet...), e só é válida a aposta que recebe um ID de transação
em "My Bets" (item 4.4). O risco real é a conta ser limitada ou fechada.

## Login
- `https://bet.asianodds88.com/login.html`: `#txtUserID`, `#txtPass`, botão `#btnDoLogin`
  (há um campo oculto `#hiddMd5Pass`: a senha é enviada em MD5).
- Após o login: `https://appNNN.asianodds88.com/UserPages/market.html` (o número do servidor muda).
- A conta do site **não** funciona na Web API (`webapi.asianodds88.com`).

## Feed de odds
- As odds chegam por WebSocket. Cada mensagem é JSON e passa pela função global `processMarketSocketMessage(msg)`.
- Tipos vistos: `EVF` (linha de mercado, formato Euro), `GN` (contagem de jogos), `L`/`RL` (liga adicionada/removida),
  `{RID,MID,SID}` (linha removida), `OPDI`/`OPD` (dados do cupom), `OUTA` (valores em aberto), Pong.
- Pedidos do cliente vão por XHR para `/AOService01/DoApiCall` (ações como `ODDSDATAREQUEST`, `OUTSTANDINGONPICKREQUEST`).
- Exemplo de `EVF` (resumido):
  ```json
  {"LID":-991904262,"MTCHID":"1640578229","HN":"America de Cali","AN":"Inter Bogota","LN":"COLOMBIA CUP",
   "MT":"Live","HS":0,"AS":0,"RCH":0,"RCA":0,"IGM":82,"EL":45,
   "FTGOAL":"1.5-2","FTOODDS":"1.555","FTOUODDS":"2.410","HTGOAL":"0.5","HTOODD":"","HTUODD":""}
  ```
  - Uma partida tem vários `LID` (linha principal + linhas alternativas), todos com o mesmo `MTCHID`.
  - `MTCHID` com sufixo `TTA`/`TTH` = gols de um time (team totals); nomes com "No. of Corners" = escanteios.
  - `IGM` = 60 + minuto no 1º tempo, 120 + minuto no 2º tempo (159 = 2T 39'). `EL` = 0 quando não há relógio.
  - `FTOODDS`/`FTOUODDS` = melhor odd Over/Under entre as casas.

## Grade de jogos
- Filtros no topo: checkboxes **Live**, Today, Early (o bot deixa só Live).
- Cada linha é `<table class="igametable matchId_<MTCHID>" id="id_<LID>">`.
- Odds clicáveis: `span.FTOver`, `span.FTUnder`, `span.HTOver`, `span.HTUnder` (todas com classe `BetItem`),
  que chamam `clickBetItem(this,'f','o','a','FTGoal')` ("a" = lado Under).

## Cupom de aposta
- Diálogo jQuery UI `#dlgPlaceBet`. Título em `#bedlg_info_caption` (ex. "FT - Over/Under: Under [1.5]").
- Uma tabela por casa: `table.iUserDataItem#ibookie<COD>` (PIN, 3ET, SBT, 198, POL, SBO, SIN, ISN, IBC...):
  `input.isCheckedForBet`, `span.spanPrice`, `span.spanMinAmount`, `span.spanMaxAmount`,
  `input.hiddRealMinAmount`, `input.hiddRealMaxAmount`, `input.hiddHDPorGoal`.
- Valor: `#betdlg_USR_AMOUNT`. Odd mínima aceita: `#betdlg_minimumprice`. Botão: `#btnDlgPlaceBetSubmit`.
- Fechar: `#dlgPlaceBetClose`. Erro: `#betdlg_inerror`. Odd média: `#betdlg_average`.
- Pode haver confirmação (`button.btnYes`); em Settings existe "Place Bet Without Confirmation".
- Na conta atual só a Pinnacle estava ativa no cupom (mín. 5 EUR).

## Ainda não verificado
O que acontece depois de "Place Bet" (mensagem de ticket, ID de transação) só dá para ver com uma aposta real.
