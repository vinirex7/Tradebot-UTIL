from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .benchmarks_v2 import equal_weight_util_curve, weighted_util_proxy_curve
from .portfolio import build_target_weights
from .regime import detect_regime
from .scoring import final_scores
from .universe import Asset


@dataclass(frozen=True)
class BacktestV2Result:
    equity_curve: pd.Series
    weighted_benchmark_curve: pd.Series
    equal_weight_benchmark_curve: pd.Series
    weights_history: pd.DataFrame
    final_portfolio: pd.DataFrame
    metrics: dict[str, float]


def monthly_rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    dates = pd.Series(index=index, data=index)
    return pd.DatetimeIndex(dates.groupby([dates.index.year, dates.index.month]).tail(1).values)


def _safe_annualized_return(curve: pd.Series) -> float:
    curve = curve.dropna()
    if len(curve) < 2 or curve.iloc[0] <= 0:
        return 0.0
    total = curve.iloc[-1] / curve.iloc[0] - 1.0
    n = max(1, len(curve) - 1)
    return float((1.0 + total) ** (252 / n) - 1.0)


def _max_drawdown(curve: pd.Series) -> float:
    curve = curve.dropna()
    if curve.empty:
        return 0.0
    return float((curve / curve.cummax() - 1.0).min())


def _daily_returns(curve: pd.Series) -> pd.Series:
    return curve.pct_change(fill_method=None).dropna()


def performance_metrics(curve: pd.Series, weighted_benchmark: pd.Series, equal_benchmark: pd.Series) -> dict[str, float]:
    common = curve.dropna().index.intersection(weighted_benchmark.dropna().index).intersection(equal_benchmark.dropna().index)
    bot = curve.reindex(common)
    weighted = weighted_benchmark.reindex(common)
    equal = equal_benchmark.reindex(common)

    bot_ret = bot.iloc[-1] / bot.iloc[0] - 1.0
    weighted_ret = weighted.iloc[-1] / weighted.iloc[0] - 1.0
    equal_ret = equal.iloc[-1] / equal.iloc[0] - 1.0

    bot_daily = _daily_returns(bot)
    weighted_daily = _daily_returns(weighted).reindex(bot_daily.index).fillna(0.0)
    equal_daily = _daily_returns(equal).reindex(bot_daily.index).fillna(0.0)

    bot_ann_return = _safe_annualized_return(bot)
    bot_ann_vol = float(bot_daily.std() * np.sqrt(252)) if len(bot_daily) else 0.0
    sharpe = float(bot_ann_return / bot_ann_vol) if bot_ann_vol > 0 else 0.0

    active_weighted = bot_daily - weighted_daily
    active_equal = bot_daily - equal_daily
    tracking_error_weighted = float(active_weighted.std() * np.sqrt(252)) if len(active_weighted) else 0.0
    tracking_error_equal = float(active_equal.std() * np.sqrt(252)) if len(active_equal) else 0.0
    information_ratio_weighted = float((active_weighted.mean() * 252) / tracking_error_weighted) if tracking_error_weighted > 0 else 0.0
    information_ratio_equal = float((active_equal.mean() * 252) / tracking_error_equal) if tracking_error_equal > 0 else 0.0

    return {
        "bot_total_return": float(bot_ret),
        "weighted_benchmark_total_return": float(weighted_ret),
        "equal_weight_benchmark_total_return": float(equal_ret),
        "alpha_vs_weighted_benchmark": float(bot_ret - weighted_ret),
        "alpha_vs_equal_weight_benchmark": float(bot_ret - equal_ret),
        "bot_annual_return": bot_ann_return,
        "bot_annual_volatility": bot_ann_vol,
        "bot_sharpe": sharpe,
        "bot_max_drawdown": _max_drawdown(bot),
        "weighted_benchmark_max_drawdown": _max_drawdown(weighted),
        "equal_weight_benchmark_max_drawdown": _max_drawdown(equal),
        "tracking_error_vs_weighted": tracking_error_weighted,
        "tracking_error_vs_equal_weight": tracking_error_equal,
        "information_ratio_vs_weighted": information_ratio_weighted,
        "information_ratio_vs_equal_weight": information_ratio_equal,
        "bot_final_value": float(bot.iloc[-1]),
        "weighted_benchmark_final_value": float(weighted.iloc[-1]),
        "equal_weight_benchmark_final_value": float(equal.iloc[-1]),
    }


def build_final_portfolio(weights: pd.Series, scores: pd.DataFrame, assets: list[Asset]) -> pd.DataFrame:
    asset_map = {asset.ticker: asset for asset in assets}
    rows = []
    for ticker, weight in weights.sort_values(ascending=False).items():
        if ticker == "CASH" or float(weight) <= 0:
            continue
        asset = asset_map.get(ticker)
        rows.append({
            "ticker": ticker,
            "name": asset.name if asset else ticker,
            "sector": asset.sector if asset else "Unknown",
            "weight": float(weight),
            "weight_pct": float(weight) * 100.0,
            "score": float(scores.loc[ticker, "score"]) if ticker in scores.index else np.nan,
        })

    cash = float(weights.get("CASH", max(0.0, 1.0 - weights.drop(labels=["CASH"], errors="ignore").sum())))
    rows.append({
        "ticker": "CASH",
        "name": "Caixa/CDI proxy",
        "sector": "Caixa",
        "weight": cash,
        "weight_pct": cash * 100.0,
        "score": np.nan,
    })
    return pd.DataFrame(rows)


def run_backtest_v2(prices: pd.DataFrame, assets: list[Asset], config: dict) -> BacktestV2Result:
    prices = prices.dropna(axis=1, how="all").ffill().dropna(how="all")
    available_assets = [asset for asset in assets if asset.ticker in prices.columns]
    if len(available_assets) < 3:
        raise ValueError("Backtest V2 needs at least 3 assets with price history")
    if len(prices) < 260:
        raise ValueError("Backtest V2 needs at least ~260 trading days")

    returns = prices.pct_change(fill_method=None).fillna(0.0)
    initial_cash = float(config.get("backtest", {}).get("initial_cash", 10000))
    cost = float(config.get("execution", {}).get("estimated_cost_per_trade", 0.002))
    min_change = float(config.get("rebalance", {}).get("min_weight_change_to_trade", 0.010))

    weights = pd.Series(0.0, index=prices.columns, dtype=float)
    equity = pd.Series(index=prices.index, dtype=float)
    equity.iloc[0] = initial_cash
    weights_rows: list[dict[str, float | str]] = []
    last_scores = pd.DataFrame(index=prices.columns)

    weighted_benchmark = weighted_util_proxy_curve(prices, available_assets, initial_cash)
    equal_benchmark = equal_weight_util_curve(prices, initial_cash)
    rebalance_dates = set(monthly_rebalance_dates(prices.index[252:]))

    for i, date in enumerate(prices.index[1:], start=1):
        day_ret = float((weights.reindex(returns.columns).fillna(0.0) * returns.loc[date]).sum())
        equity.iloc[i] = equity.iloc[i - 1] * (1.0 + day_ret)

        if date in rebalance_dates:
            history = prices.loc[:date]
            last_scores = final_scores(history, config)
            regime = detect_regime(history, config)
            target = build_target_weights(last_scores, available_assets, regime.equity_exposure, config)
            target = target.reindex(prices.columns).fillna(0.0)

            turnover = float((target - weights).abs().sum())
            if turnover >= min_change:
                equity.iloc[i] *= 1.0 - turnover * cost
                weights = target

            row: dict[str, float | str] = {ticker: float(weights.get(ticker, 0.0)) for ticker in prices.columns}
            row["CASH"] = max(0.0, 1.0 - float(weights.sum()))
            row["REGIME"] = regime.regime
            row["EQUITY_EXPOSURE"] = float(regime.equity_exposure)
            row["TURNOVER"] = turnover
            row["DATE"] = str(date.date())
            weights_rows.append(row)

    weights_with_cash = weights.copy()
    weights_with_cash.loc["CASH"] = max(0.0, 1.0 - float(weights.sum()))
    final_portfolio = build_final_portfolio(weights_with_cash, last_scores, available_assets)
    weights_history = pd.DataFrame(weights_rows).set_index("DATE") if weights_rows else pd.DataFrame()
    metrics = performance_metrics(equity, weighted_benchmark, equal_benchmark)

    return BacktestV2Result(
        equity_curve=equity,
        weighted_benchmark_curve=weighted_benchmark,
        equal_weight_benchmark_curve=equal_benchmark,
        weights_history=weights_history,
        final_portfolio=final_portfolio,
        metrics=metrics,
    )


def save_backtest_v2(result: BacktestV2Result, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    result.equity_curve.to_csv(out / "equity_curve_v2.csv", header=["bot"])
    result.weighted_benchmark_curve.to_csv(out / "benchmark_weighted_util_proxy.csv", header=["weighted_UTIL_proxy"])
    result.equal_weight_benchmark_curve.to_csv(out / "benchmark_equal_weight_util.csv", header=["equal_weight_UTIL"])
    result.weights_history.to_csv(out / "weights_history_v2.csv")
    result.final_portfolio.to_csv(out / "final_portfolio_v2.csv", index=False)
    pd.DataFrame({"metric": list(result.metrics.keys()), "value": list(result.metrics.values())}).to_csv(out / "metrics_v2.csv", index=False)

    combined = pd.concat([
        result.equity_curve.rename("bot"),
        result.weighted_benchmark_curve.rename("weighted_UTIL_proxy"),
        result.equal_weight_benchmark_curve.rename("equal_weight_UTIL"),
    ], axis=1)
    combined.to_csv(out / "comparison_curves_v2.csv")
    return out
