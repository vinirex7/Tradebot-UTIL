# Documento Técnico — Tradebot UTIL / UTIL Modern Regime Allocation

## 1. Visão geral

O Tradebot UTIL é um robô quantitativo long-only especializado nas ações que compõem o Índice Utilidade Pública da B3.

Ele usa o UTIL como universo de investimento e benchmark, mas não replica cegamente o índice. A proposta é montar uma carteira ativa que aumente peso nas melhores ações e reduza peso nas piores.

## 2. Objetivo

Superar o UTIL no ciclo completo, buscando retorno líquido maior, drawdown controlado e melhor relação risco-retorno.

## 3. Regras centrais

- Operar somente ações do UTIL.
- Usar preços ajustados por proventos.
- Rebalancear mensalmente.
- Fazer checagem de risco semanal na evolução futura.
- Não usar alavancagem.
- Não fazer short.
- Não fazer day trade.
- Usar caixa/CDI quando o regime estiver ruim.

## 4. Universo inicial

```text
AXIA3, SBSP3, EQTL3, ENEV3, CPLE3, CMIG4, ENGI11, EGIE3,
ISAE4, CSMG3, TAEE11, CPFE3, SAPR11, ALUP11, ORVR3, AURE3
```

## 5. Score

```text
ScoreFinal = 35% Momentum Relativo
           + 20% Momentum Absoluto
           + 15% Qualidade
           + 15% Risco
           + 10% Dividendos
           + 5% Liquidez
           - Penalidades
```

Na versão inicial, qualidade e dividendos entram como score neutro quando não houver base fundamentalista carregada. Isso evita inventar dado fundamentalista no backtest.

## 6. Regime

Regimes possíveis:

```text
RISK_ON
NEUTRAL
DEFENSIVE
RISK_OFF
```

A exposição em ações varia conforme regime:

```text
RISK_ON   -> 95%
NEUTRAL   -> 80%
DEFENSIVE -> 55%
RISK_OFF  -> 30%
```

## 7. Construção da carteira

O bot parte dos pesos oficiais do UTIL e aplica um tilt ativo conforme o score de cada ação.

Restrições iniciais:

```text
Mínimo de posições: 5
Máximo de posições: 10
Peso mínimo por ativo: 3%
Peso máximo por ativo: 18%
Peso máximo nas 3 maiores posições: 50%
Peso máximo em energia elétrica: 85%
Peso máximo em saneamento: 35%
```

## 8. Compra

Comprar ou aumentar posição quando:

```text
ScoreFinal >= 65
Preço acima da média móvel de 100 dias
Retorno de 6 meses positivo
Ativo não estiver excessivamente esticado
Liquidez suficiente
```

## 9. Venda

Vender ou reduzir quando:

```text
ScoreFinal < 45
Preço abaixo da média móvel de 200 dias
Momentum de 6 meses negativo
Drawdown desde topo maior que 15%
Ativo saiu do UTIL
```

## 10. Backtest

O backtest inicial deve comparar contra:

```text
UTIL
Carteira equal weight do UTIL
IBOV
CDI
```

Métricas principais:

```text
Retorno acumulado
Retorno anualizado
Volatilidade anualizada
Sharpe
Maximum Drawdown
Alpha contra benchmark
Tracking Error
Information Ratio
Turnover
```

## 11. Próximas versões

V2:

- adicionar fundamentos reais;
- adicionar dividendos reais;
- adicionar curva de juros;
- adicionar atualização automática da carteira B3;
- adicionar walk-forward test.

V3:

- integração com corretora;
- execução paper/live;
- dashboard;
- alertas Telegram;
- monitoramento em VPS.
