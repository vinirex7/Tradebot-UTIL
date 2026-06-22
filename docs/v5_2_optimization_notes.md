# V5.2 optimization notes

These notes document the next optimization pass suggested after the latest backtests.

## Problem observed

The V5 configuration produced positive absolute returns, but underperformed the primary UTIL benchmark, the weighted proxy, and the equal-weight proxy in the tested windows. The main issue appears to be excessive cash drag and a portfolio that is neither defensive enough to reduce drawdown nor aggressive enough to outperform during sector rallies.

## Suggested parameter changes

Recommended changes for `config_v5.yaml`:

```yaml
strategy:
  version: 5.2

regime:
  risk_on_equity: 1.00
  neutral_equity: 1.00
  defensive_equity: 0.90
  risk_off_equity: 0.65

portfolio_v4:
  min_positions: 6
  max_positions: 10
  max_weight_per_asset: 0.22
  max_top3_weight: 0.60
  score_power: 1.45
  target_volatility: 0.26
  vol_scalar_floor: 0.75
  max_cash_by_regime:
    RISK_ON: 0.02
    NEUTRAL: 0.05
    DEFENSIVE: 0.15
    RISK_OFF: 0.35
  min_equity_exposure: 0.60
  minimum_score_edge: 50

score_weights:
  relative_momentum: 0.40
  absolute_momentum: 0.25
  risk: 0.20
  liquidity: 0.05
  quality: 0.05
  dividends: 0.05

buy_rules:
  min_score_to_buy: 54
  top_rank_exception_count: 6

sell_rules:
  reduce_score_below: 48
  sell_score_below: 40
  trailing_drawdown_from_peak: 0.22

risk:
  portfolio_drawdown_reduce_1: 0.12
  portfolio_drawdown_reduce_2: 0.18
  portfolio_drawdown_protection: 0.26
  max_single_asset_drawdown: 0.22
```

## Why

- Reduce cash drag in a defensive equity sector.
- Increase diversification from 5-8 names to 6-10 names.
- Lower max single-name and top-3 concentration.
- Keep the model momentum-first, but reduce overdependence on short-term relative momentum.
- Make defensive regimes reduce risk without abandoning equity exposure too early.

## Validation commands

```bash
python3 main_v5.py backtest \
  --config config_v5.yaml \
  --benchmark-csv data/benchmarks/UTIL_historico.csv \
  --update-universe-first \
  --universe-csv data/universe/UTIL_carteira_atual.csv \
  --start-date 2021-01-01 \
  --end-date 2026-06-20 \
  --output-dir backtests/results_v5_2_2021

python3 main_v5.py backtest \
  --config config_v5.yaml \
  --benchmark-csv data/benchmarks/UTIL_historico.csv \
  --update-universe-first \
  --universe-csv data/universe/UTIL_carteira_atual.csv \
  --start-date 2024-01-01 \
  --end-date 2026-06-20 \
  --output-dir backtests/results_v5_2_2024
```
