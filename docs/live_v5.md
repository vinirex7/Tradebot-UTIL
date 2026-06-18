# Live/Paper V5 — Tradebot UTIL

A V5 é a estratégia atual recomendada para avançar rumo ao live, porque combina:

- universo dinâmico do UTIL;
- benchmark real do UTIL via CSV;
- lógica de regime e carteira alinhada ao backtest V4/V5;
- geração de decisão live;
- modo `dry-run` e modo `paper`.

## Situação atual da corretora

Nenhuma corretora real está conectada ainda.

A execução real permanece bloqueada por segurança. O código só permite:

```text
dry-run
paper
```

Para operar dinheiro real será necessário implementar um `BrokerAdapter` específico da corretora escolhida.

## Arquivos adicionados

```text
tradebot_util/strategy_live_v5.py
tradebot_util/live_executor_v5.py
tradebot_util/broker_base.py
tradebot_util/brokers/paper.py
tradebot_util/brokers/null_broker.py
scripts/run_live_paper_v5.sh
docs/live_v5.md
```

## Como gerar uma decisão live sem ordens

```bash
python3 main_v5.py decide \
  --config config_v5.yaml \
  --benchmark-csv data/benchmarks/UTIL_historico.csv \
  --universe-csv data/universe/UTIL_carteira_atual.csv \
  --update-universe-first \
  --output-dir state/live
```

Esse comando salva:

```text
state/live/target_weights.csv
state/live/scores.csv
state/live/decision_summary.csv
```

## Como rodar ciclo paper

```bash
python3 main_v5.py live-cycle \
  --config config_v5.yaml \
  --benchmark-csv data/benchmarks/UTIL_historico.csv \
  --universe-csv data/universe/UTIL_carteira_atual.csv \
  --update-universe-first \
  --mode paper \
  --apply-paper-targets \
  --output-dir state/live
```

Esse comando gera intenções de ordem e aplica os pesos em uma carteira simulada local.

Arquivos principais:

```text
state/live/order_intents.csv
state/paper/positions.csv
```

## Script pronto

```bash
bash scripts/run_live_paper_v5.sh
```

## Rodar continuamente na VPS

Recomendação segura para a V5: rodar paper trading diariamente ou semanalmente antes de qualquer execução real.

Exemplo com cron diário às 18:30:

```bash
crontab -e
```

Adicionar:

```cron
30 18 * * 1-5 cd /root/Tradebot-UTIL && bash scripts/run_live_paper_v5.sh
```

## Por que não rodar ordem real ainda

Ainda falta:

1. Escolher corretora com API para B3.
2. Implementar o adapter real.
3. Validar lote mínimo, custos, horários de pregão e status das ordens.
4. Implementar cancelamento/reenvio de ordens.
5. Rodar paper por algumas semanas.
6. Só então liberar execução real com trava explícita.

## Alinhamento com o backtest

A decisão live V5 usa a mesma base da estratégia do backtest:

- `detect_regime` com benchmark real, quando disponível;
- `final_scores`;
- `build_target_weights_v4`;
- universo ativo dinâmico da V5.

Isso corrige a diferença anterior em que o comando `rank` podia calcular regime sem passar o benchmark real.
