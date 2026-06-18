from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .portfolio import build_target_weights
from .regime import detect_regime
from .scoring import final_scores
from .universe import Asset


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.Series
    benchmark_curve: pd.Series
    weights_history: pd.DataFrame
    metrics: dict[str, float]


def _monthly_rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    dates = pd.Series(index=index, data=index)
    return pd.DatetimeIndex(dates.groupby([dates.index.year, dates.index.month]).tail(1).values)


def _performance_metrics(curve: pd.Series, benchmark: pd.Series) -> dict[str, float]:
    curve = curve.dropna()
    benchmark = benchmark.reindex(curve.index).dropna()
    common = curve.index.intersection(benchmark.index)
    curve = curve.reindex(common)
    benchmark = benchmark.reindex(common)

    returns = curve.pct_change(fill_method=None).dropna()
    bench_returns = benchmark.pct_change(fill_method=None).dropna().reindex(returns.index).fillna(0.0)

    total_return = float(curve.iloc[-1] / curve.iloc[0] - 1.0) if len(curve) > 1 else 0.0
    annual_return = float((1.0 + total_return) ** (252 / max(1, len(returns))) - 1.0) if len(returns) else 0.0
    annual_vol = float(returns.std() * np.sqrt(252)) if len(returns) else 0.0
    sharpe = float(annual_return / annual_vol) if annual_vol > 0 else 0.0
    max_dd = float((curve / curve.cummax() - 1.0).min()) if len(curve) else 0.0

    active = returns - bench_returns
    tracking_error = float(active.std() * np.sqrt(252)) if len(active) else 0.0
    alpha = float(total_return - (benchmark.iloc[-1] / benchmark.iloc[0] - 1.0)) if len(benchmark) > 1 else 0.0
    information_ratio = float((active.mean() * 252) / tracking_error) if tracking_error > 0 else 0.0

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "annual_volatility": annual_vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "alpha_vs_benchmark": alpha,
        "tracking_error": tracking_error,
        "information_ratio": information_ratio,
    }


def run_backtest(prices: pd.DataFrame, assets: list[Asset], config: dict) -> BacktestResult:
    prices = prices.dropna(axis=1, how="all").ffill().dropna(how="all")
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    if len(prices) < 260:
        raise ValueError("Backtest needs at least ~260 trading days")

    initial_cash = float(config.get("backtest", {}).get("initial_cash", 10000))
    cost = float(config.get("execution", {}).get("estimated_cost_per_trade", 0.002))
    min_change = float(config.get("rebalance", {}).get("min_weight_change_to_trade", 0.015))

    weights = pd.Series(0.0, index=prices.columns)
    equity = pd.Series(index=prices.index, dtype=float)
    equity.iloc[0] = initial_cash
    weights_rows: list[pd.Series] = []
    rebalance_dates = set(_monthly_rebalance_dates(prices.index[252:]))

    for i, date in enumerate(prices.index[1:], start=1):
        day_ret = float((weights.reindex(returns.columns).fillna(0.0) * returns.loc[date]).sum())
        equity.iloc[i] = equity.iloc[i - 1] * (1.0 + day_ret)

        if date in rebalance_dates:
            history = prices.loc[:date]
            scores = final_scores(history, config)
            regime = detect_regime(history, config)
            target = build_target_weights(scores, assets, regime.equity_exposure, config)
            target = target.reindex(prices.columns).fillna(0.0)

            turnover = float((target - weights).abs().sum())
            if turnover >= min_change:
                equity.iloc[i] *= 1.0 - turnover * cost
                weights = target
                row = target.copy()
                row.name = date
                row["CASH"] = max(0.0, 1.0 - float(target.sum()))
                row["REGIME"] = regime.regime
                weights_rows.append(row)

    benchmark_returns = returns.mean(axis=1)
    benchmark_curve = initial_cash * (1.0 + benchmark_returns).cumprod()
    metrics = _performance_metrics(equity, benchmark_curve)
    weights_history = pd.DataFrame(weights_rows)
    return BacktestResult(equity, benchmark_curve, weights_history, metrics)
