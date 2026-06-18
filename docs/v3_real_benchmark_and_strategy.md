# Upgrade V3 — Benchmark real e estratégia melhorada

A V3 foi criada sem apagar V1 e V2.

## Arquivos novos

```text
config_v3.yaml
main_v3.py
tradebot_util/benchmark_real_v3.py
tradebot_util/portfolio_v3.py
tradebot_util/backtest_v3.py
scripts/show_v3_results.py
docs/v3_real_benchmark_and_strategy.md
tests/test_backtest_v3.py
```

## O que mudou

### 1. Benchmark real do UTIL via CSV

A V3 aceita uma série histórica real do UTIL em CSV.

Formato recomendado:

```csv
date,close
2019-01-02,5723
2019-01-03,5750
```

Também são aceitas colunas com nomes como:

```text
Data, Fechamento, Pontuação, Pontuacao, Último, Ultimo
```

O arquivo padrão esperado é:

```text
data/benchmarks/UTIL_historico.csv
```

Se esse arquivo existir, o benchmark primário passa a ser `real_UTIL_csv`.

Se não existir, a V3 usa o proxy ponderado, a menos que você rode com `--strict-real-benchmark`.

### 2. Estratégia V3 para melhorar Sharpe e drawdown

A V3 adiciona:

- seleção mais concentrada nas melhores ações;
- score com mais peso em momentum;
- ponderação por volatilidade inversa;
- alvo de volatilidade da carteira;
- controle de exposição por regime;
- suporte a janelas específicas de backtest.

Isso busca melhorar Sharpe e drawdown, mas não garante superar o índice. A melhoria precisa ser validada por backtest e walk-forward.

### 3. Backtest por janela

Agora é possível rodar:

```bash
python main_v3.py backtest --config config_v3.yaml --start-date 2023-01-01
python main_v3.py backtest --config config_v3.yaml --start-date 2025-01-01
```

Para benchmark real obrigatório:

```bash
python main_v3.py backtest --config config_v3.yaml --benchmark-csv data/benchmarks/UTIL_historico.csv --strict-real-benchmark
```

## Comandos principais

Atualizar VPS:

```bash
git pull
```

Rodar testes:

```bash
pytest -q
```

Backtest V3 completo:

```bash
python main_v3.py backtest --config config_v3.yaml
```

Backtest V3 com benchmark real obrigatório:

```bash
python main_v3.py backtest --config config_v3.yaml --benchmark-csv data/benchmarks/UTIL_historico.csv --strict-real-benchmark
```

Backtest últimos 3 anos:

```bash
python main_v3.py backtest --config config_v3.yaml --start-date 2023-06-18 --output-dir backtests/results_v3_3y
```

Backtest último ano:

```bash
python main_v3.py backtest --config config_v3.yaml --start-date 2025-06-18 --output-dir backtests/results_v3_1y
```

Resumo da V3:

```bash
python scripts/show_v3_results.py
```

## Observação importante

Para resultado fiel à realidade, use a série histórica oficial do UTIL. O proxy ponderado é apenas uma aproximação e não deve ser tratado como índice oficial.
