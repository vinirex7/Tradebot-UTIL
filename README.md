# Tradebot-UTIL

Tradebot quantitativo especializado no **Índice de Utilidade Pública da B3 (UTIL)**.

A estratégia usa as ações do UTIL como universo de investimento, mas não copia o índice. O objetivo é montar uma carteira long-only com rebalanceamento periódico, pesos dinâmicos por ativo e controle de risco, buscando superar o UTIL no ciclo completo.

## Filosofia

O bot funciona como um gestor automático de utilities brasileiras:

- usa apenas ações da carteira do UTIL;
- calcula score individual por ativo;
- aumenta peso nas melhores ações;
- reduz ou zera ações fracas;
- controla concentração;
- reduz exposição quando o regime do setor piora;
- usa caixa/CDI como proteção em regimes ruins.

O projeto **não** usa alavancagem, short, futuros, margem, opções ou day trade na versão inicial.

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

## Comandos principais

Mostrar universo e configuração:

```bash
python main.py show-config --config config.yaml
```

Calcular ranking atual:

```bash
python main.py rank --config config.yaml
```

Rodar backtest:

```bash
python main.py backtest --config config.yaml
```

Rodar testes:

```bash
pytest -q
```

## Segurança

Nunca coloque chaves de corretora, senhas, tokens ou arquivos `.env` no GitHub.

A execução real em corretora deve ser implementada somente depois de backtests, simulação e validação operacional.
