# Tradebot-UTIL

Tradebot quantitativo especializado no **Índice de Utilidade Pública da B3 (UTIL)**.

A estratégia usa as ações do UTIL como universo de investimento, mas não copia o índice. O objetivo é montar uma carteira long-only com rebalanceamento periódico, pesos dinâmicos por ativo e controle de risco, buscando superar o UTIL no ciclo completo.

## Versão atual

A versão operacional atual é a **V5.3 Alpha**.

Ela foi ajustada depois dos backtests em que a V5.2 ficou muito parecida com o benchmark: retorno próximo ao UTIL, mas drawdown quase igual. A V5.3 tenta melhorar isso com três mudanças centrais:

- **momentum relativo ao benchmark UTIL**: o ativo só ganha overweight se estiver melhorando contra o índice, não apenas subindo junto com o setor;
- **regime mais defensivo do próprio UTIL**: quando o índice perde SMA200, momentum ou entra em drawdown relevante, a exposição cai mais forte;
- **core-satellite controlado**: parte da carteira fica ancorada nos pesos do índice para evitar apostas extremas, e parte busca alpha nos melhores scores.

O projeto **não** usa alavancagem, short, futuros, margem, opções ou day trade.

## Universo inicial

```text
AXIA3, SBSP3, EQTL3, ENEV3, CPLE3, CMIG4, ENGI11, EGIE3,
ISAE4, CSMG3, TAEE11, CPFE3, SAPR11, ALUP11, ORVR3, AURE3
```

A composição deve ser revisada quando a B3 atualizar a carteira teórica do UTIL.

## Instalação local ou VPS Ubuntu

```bash
git clone https://github.com/vinirex7/Tradebot-UTIL.git
cd Tradebot-UTIL

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

## Comandos principais V5.3

Mostrar configuração:

```bash
python3 main_v5.py show-config --config config_v5.yaml
```

Atualizar universo antes de decidir/backtestar:

```bash
python3 main_v5.py update-universe --config config_v5.yaml --universe-csv data/universe/UTIL_carteira_atual.csv
```

Calcular ranking atual:

```bash
python3 main_v5.py rank --config config_v5.yaml --benchmark-csv data/benchmarks/UTIL_historico.csv --update-universe-first --universe-csv data/universe/UTIL_carteira_atual.csv
```

Gerar decisão sem enviar ordens:

```bash
python3 main_v5.py decide --config config_v5.yaml --benchmark-csv data/benchmarks/UTIL_historico.csv --update-universe-first --universe-csv data/universe/UTIL_carteira_atual.csv
```

Rodar backtest principal:

```bash
python3 main_v5.py backtest --config config_v5.yaml --benchmark-csv data/benchmarks/UTIL_historico.csv --update-universe-first --universe-csv data/universe/UTIL_carteira_atual.csv --start-date 2025-06-01 --end-date 2026-06-20 --output-dir backtests/results_v5_3
```

Rodar backtest 2026:

```bash
python3 main_v5.py backtest --config config_v5.yaml --benchmark-csv data/benchmarks/UTIL_historico.csv --update-universe-first --universe-csv data/universe/UTIL_carteira_atual.csv --start-date 2026-01-01 --end-date 2026-06-20 --output-dir backtests/results_v5_3_2026
```

Rodar paper/dry-run:

```bash
python3 main_v5.py live-cycle --mode paper --config config_v5.yaml --benchmark-csv data/benchmarks/UTIL_historico.csv --update-universe-first --universe-csv data/universe/UTIL_carteira_atual.csv --apply-paper-targets
```

Ver últimas decisões salvas:

```bash
tail -20 state/live/decision_summary.csv
tail -20 state/live/target_weights.csv
tail -20 state/live/scores.csv
```

Rodar testes:

```bash
pytest -q
```

## Como avaliar se superou o UTIL

Não olhe só retorno final. A V5.3 deve ser comparada contra:

- retorno total do UTIL;
- alpha vs UTIL;
- max drawdown vs UTIL;
- drawdown_reduction_vs_primary;
- Sharpe do bot vs Sharpe do benchmark;
- information ratio vs primary benchmark.

O resultado ideal é o bot ter retorno maior que o UTIL **ou** retorno parecido com drawdown menor e Sharpe superior.

## Segurança

Nunca coloque chaves de corretora, senhas, tokens ou arquivos `.env` no GitHub.

A execução real em corretora deve ser implementada somente depois de backtests, simulação e validação operacional.
