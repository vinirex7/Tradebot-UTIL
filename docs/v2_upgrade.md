# Upgrade V2 — Tradebot UTIL

A V2 foi criada sem apagar a base V1.

## Arquivos novos

```text
config_v2.yaml
main_v2.py
tradebot_util/benchmarks_v2.py
tradebot_util/backtest_v2.py
scripts/show_v2_results.py
tests/test_backtest_v2.py
docs/v2_upgrade.md
```

## Principais mudanças

### 1. Benchmark melhorado

A V1 comparava o bot contra um proxy equal-weight. A V2 salva dois benchmarks:

```text
benchmark_weighted_util_proxy.csv
benchmark_equal_weight_util.csv
```

O benchmark ponderado usa os pesos do `config_v2.yaml` normalizados entre os ativos com histórico disponível.

### 2. Estratégia menos defensiva

A V1 ficava defensiva cedo demais. A V2 usa maior exposição em ações:

```text
RISK_ON   -> 100%
NEUTRAL   -> 95%
DEFENSIVE -> 75%
RISK_OFF  -> 45%
```

### 3. Score com mais peso em momentum

Como ainda não carregamos fundamentos e dividendos reais, a V2 reduz o peso desses scores neutros e aumenta o peso de momentum.

```text
relative_momentum: 45%
absolute_momentum: 25%
risk: 15%
quality: 5%
dividends: 5%
liquidity: 5%
```

### 4. Relatórios mais legíveis

A V2 salva:

```text
equity_curve_v2.csv
benchmark_weighted_util_proxy.csv
benchmark_equal_weight_util.csv
comparison_curves_v2.csv
weights_history_v2.csv
final_portfolio_v2.csv
metrics_v2.csv
```

## Comandos

Atualizar VPS:

```bash
git pull
```

Rodar testes:

```bash
pytest -q
```

Ver configuração V2:

```bash
python main_v2.py show-config --config config_v2.yaml
```

Rodar ranking V2:

```bash
python main_v2.py rank --config config_v2.yaml
```

Rodar backtest V2:

```bash
python main_v2.py backtest --config config_v2.yaml
```

Ver resumo após o backtest:

```bash
python scripts/show_v2_results.py
```

## Observação importante

O benchmark ponderado da V2 ainda é um proxy, não a série oficial histórica do UTIL da B3. Ele usa os pesos atuais do índice aplicados ao histórico disponível. É mais justo que o equal-weight puro, mas ainda não substitui a série oficial histórica do índice.
