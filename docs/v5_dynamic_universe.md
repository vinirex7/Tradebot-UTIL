# V5 — Universo dinâmico do UTIL

A V5 foi criada para resolver uma limitação das versões anteriores: a lista de ações do UTIL ficava fixa no `config.yaml`.

Agora o bot pode atualizar mensalmente quais ações fazem parte do índice e quais pesos serão usados como referência.

## O que a V5 faz

- Lê uma carteira atual do UTIL em CSV.
- Detecta ações adicionadas.
- Detecta ações removidas.
- Normaliza os pesos do índice.
- Salva um universo ativo.
- Usa esse universo ativo no ranking e no backtest.

## Arquivos novos

```text
config_v5.yaml
main_v5.py
tradebot_util/universe_dynamic_v5.py
data/universe/README.md
scripts/monthly_universe_update.sh
docs/v5_dynamic_universe.md
tests/test_universe_dynamic_v5.py
```

## Arquivo de entrada

Coloque a carteira atual do UTIL em:

```text
data/universe/UTIL_carteira_atual.csv
```

Formato recomendado:

```csv
ticker,name,sector,index_weight
AXIA3,Axia Energia,Energia Elétrica,19.77%
SBSP3,Sabesp,Água e Saneamento,18.85%
EQTL3,Equatorial Energia,Energia Elétrica,11.81%
```

Também são aceitas colunas como:

```text
Código
Codigo
Ativo
Nome
Setor
Part. (%)
Participação
Peso
```

## Atualizar universo

```bash
python3 main_v5.py update-universe --config config_v5.yaml --universe-csv data/universe/UTIL_carteira_atual.csv
```

O comando gera:

```text
data/universe/UTIL_universe_active.csv
data/universe/UTIL_universe_update_report.csv
```

O relatório mostra ativos adicionados, removidos e mantidos.

## Ver universo ativo

```bash
python3 main_v5.py show-universe --config config_v5.yaml
```

## Rodar ranking com universo atualizado

```bash
python3 main_v5.py rank --config config_v5.yaml --update-universe-first --universe-csv data/universe/UTIL_carteira_atual.csv
```

## Rodar backtest com universo atualizado

```bash
python3 main_v5.py backtest --config config_v5.yaml --benchmark-csv data/benchmarks/UTIL_historico.csv --strict-real-benchmark --update-universe-first --universe-csv data/universe/UTIL_carteira_atual.csv --output-dir backtests/results_v5_real_full
```

## Automação mensal

A V5 inclui o script:

```bash
bash scripts/monthly_universe_update.sh
```

Esse script lê `data/universe/UTIL_carteira_atual.csv` e atualiza o universo ativo.

Para agendar no cron uma vez por mês:

```bash
crontab -e
```

Adicionar:

```cron
0 8 1 * * cd /root/Tradebot-UTIL && bash scripts/monthly_universe_update.sh >> logs/universe_update.log 2>&1
```

Isso roda todo dia 1 de cada mês às 08:00.

## Observação importante

A V5 automatiza a leitura, comparação e aplicação do universo atualizado. Mas ela ainda precisa que o arquivo `UTIL_carteira_atual.csv` seja atualizado com uma fonte confiável. Se a B3 disponibilizar um endpoint estável no futuro, ele poderá ser ligado diretamente aqui.

## Em versão live

Quando uma ação sai do UTIL, ela deixa de fazer parte do universo ativo. Em uma versão conectada à corretora, a rotina de execução deve zerar posições em ativos removidos e redistribuir o capital entre os ativos restantes conforme score e regime.
