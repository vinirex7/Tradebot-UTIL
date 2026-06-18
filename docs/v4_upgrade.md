# Upgrade V4 — Rebalanceamento semanal de risco e menos caixa em bull market

A V4 foi criada sem apagar V1, V2 ou V3.

## Arquivos novos

```text
config_v4.yaml
main_v4.py
tradebot_util/portfolio_v4.py
tradebot_util/backtest_v4.py
scripts/show_v4_results.py
docs/v4_upgrade.md
tests/test_backtest_v4.py
```

## Por que a V4 existe

A V3 funcionou com benchmark real do UTIL, mas ainda ficou conservadora demais. Em alguns testes, a carteira terminou com cerca de 60% em caixa. Isso reduziu risco em alguns momentos, mas também segurou o retorno e não foi suficiente para superar o índice.

A V4 tenta corrigir isso.

## Mudanças principais

### 1. Menos caixa em regimes bons

A V4 limita o caixa máximo por regime:

```text
RISK_ON   -> caixa máximo 5%
NEUTRAL   -> caixa máximo 10%
DEFENSIVE -> caixa máximo 28%
RISK_OFF  -> caixa máximo 55%
```

Isso força o bot a ficar mais comprado quando o regime está favorável.

### 2. Benchmark real também usado no regime

A V4 usa a série real do UTIL, quando disponível, para detectar regime de mercado. Isso deixa a decisão de exposição mais fiel ao benchmark oficial.

### 3. Rebalanceamento mensal + checagem semanal

A V4 mantém rebalanceamento mensal, mas adiciona checagem semanal de risco.

- mensal: recalcula carteira completa;
- semanal: recalcula se houver mudança de regime ou diferença relevante de exposição.

### 4. Otimizador V4

A carteira agora usa:

- score mais focado em momentum;
- bonus de tendência;
- volatilidade inversa;
- limite de peso por ação;
- limite das 3 maiores posições;
- alvo de volatilidade aplicado principalmente em defesa.

## Comandos

Atualizar VPS:

```bash
cd ~/Tradebot-UTIL
git pull
source venv/bin/activate
```

Rodar testes:

```bash
pytest -q
```

Backtest V4 completo com benchmark real obrigatório:

```bash
python3 main_v4.py backtest --config config_v4.yaml --benchmark-csv data/benchmarks/UTIL_historico.csv --strict-real-benchmark --output-dir backtests/results_v4_real_full
```

Backtest V4 dos últimos 3 anos:

```bash
python3 main_v4.py backtest --config config_v4.yaml --benchmark-csv data/benchmarks/UTIL_historico.csv --strict-real-benchmark --start-date 2023-06-18 --output-dir backtests/results_v4_real_3y
```

Backtest V4 do último ano:

```bash
python3 main_v4.py backtest --config config_v4.yaml --benchmark-csv data/benchmarks/UTIL_historico.csv --strict-real-benchmark --start-date 2025-06-18 --output-dir backtests/results_v4_real_1y
```

Ver métricas:

```bash
cat backtests/results_v4_real_full/metrics_v4.csv
cat backtests/results_v4_real_3y/metrics_v4.csv
cat backtests/results_v4_real_1y/metrics_v4.csv
```

## Atenção

A V4 é uma evolução quantitativa, não uma garantia de superar o índice. O objetivo agora é testar se menos caixa em bull market e rebalanceamento semanal de risco melhoram retorno, Sharpe e drawdown.
