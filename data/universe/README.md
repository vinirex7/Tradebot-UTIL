# Universo dinâmico do UTIL

A V5 permite atualizar mensalmente a lista de ações do UTIL sem editar o `config.yaml` manualmente.

## Arquivo esperado

Coloque a carteira atual do UTIL em:

```text
data/universe/UTIL_carteira_atual.csv
```

O arquivo pode vir da B3 ou de outra fonte confiável, desde que tenha pelo menos uma coluna de ticker e, idealmente, peso.

Formatos aceitos:

```csv
ticker,name,sector,index_weight
AXIA3,Axia Energia,Energia Elétrica,19.77%
SBSP3,Sabesp,Água e Saneamento,18.85%
```

Também aceita colunas como:

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

Se o peso vier em porcentagem, como `19,77` ou `19.77%`, o bot converte e normaliza automaticamente.

## Comando para atualizar

```bash
python3 main_v5.py update-universe --config config_v5.yaml --universe-csv data/universe/UTIL_carteira_atual.csv
```

Isso gera:

```text
data/universe/UTIL_universe_active.csv
data/universe/UTIL_universe_update_report.csv
```

O relatório mostra ativos adicionados, removidos e mantidos.

## Como o bot usa isso

Depois da atualização, a V5 usa `UTIL_universe_active.csv` como universo oficial do bot.

Se uma ação entrou no UTIL, ela passa a ser considerada no ranking e pode receber peso na carteira.

Se uma ação saiu do UTIL, ela deixa de ser considerada. Em uma versão live com corretora, a rotina de rebalanceamento deverá zerar ativos que não estão mais no universo ativo.

## Automação mensal

A V5 tem suporte a atualização mensal, mas o arquivo `UTIL_carteira_atual.csv` precisa estar atualizado. O caminho seguro é baixar a carteira nova da B3/Investing/Status Invest e salvar com esse nome antes de rodar o comando.
