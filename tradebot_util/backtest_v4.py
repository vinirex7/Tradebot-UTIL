from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .benchmark_real_v3 import build_benchmark_curves
from .portfolio_v4 import build_target_weights_v4
from .regime import detect_regime
from .scoring import final_scores
from .universe import Asset


@dataclass(frozen=True)
class BacktestV4Result:
    equity_curve: pd.Series
    primary_benchmark_curve: pd.Series
    weighted_benchmark_curve: pd.Series
    equal_weight_benchmark_curve: pd.Series
    weights_history: pd.DataFrame
    final_portfolio: pd.DataFrame
    metrics: dict[str, float]
    primary_benchmark_name: str


def filter_by_date(prices: pd.DataFrame, start_date: str | None = None, end_date: str | None = None, warmup_days: int = 252) -> pd.DataFrame:
    data = prices.copy().sort_index()
    if start_date:
        start_ts = pd.Timestamp(start_date)
        warmup_start_idx = max(0, data.index.searchsorted(start_ts) - warmup_days)
        data = data.iloc[warmup_start_idx:]
        data.attrs["trade_start_date"] = str(start_ts.date())
    if end_date:
        data = data.loc[:pd.Timestamp(end_date)]
    return data


def monthly_rebalance_dates(index: pd.DatetimeIndex, trade_start_date: str | None = None) -> pd.DatetimeIndex:
    trade_index = index[index >= pd.Timestamp(trade_start_date)] if trade_start_date else index
    dates = pd.Series(index=trade_index, data=trade_index)
    if dates.empty:
        return pd.DatetimeIndex([])
    return pd.DatetimeIndex(dates.groupby([dates.index.year, dates.index.month]).tail(1).values)


def weekly_check_dates(index: pd.DatetimeIndex, trade_start_date: str | None = None) -> pd.DatetimeIndex:
    trade_index = index[index >= pd.Timestamp(trade_start_date)] if trade_start_date else index
    dates = pd.Series(index=trade_index, data=trade_index)
    if dates.empty:
        return pd.DatetimeIndex([])
    iso = dates.index.isocalendar()
    return pd.DatetimeIndex(dates.groupby([iso.year, iso.week]).tail(1).values)


def _ret(curve: pd.Series) -> pd.Series:
    return curve.pct_change(fill_method=None).dropna()


def _ann_return(curve: pd.Series) -> float:
    curve = curve.dropna()
    if len(curve) < 2 or curve.iloc[0] <= 0:
        return 0.0
    total = curve.iloc[-1] / curve.iloc[0] - 1.0
    return float((1.0 + total) ** (252 / max(1, len(curve) - 1)) - 1.0)


def _ann_vol(curve: pd.Series) -> float:
    r = _ret(curve)
    return float(r.std() * np.sqrt(252)) if len(r) else 0.0


def _max_dd(curve: pd.Series) -> float:
    curve = curve.dropna()
    return float((curve / curve.cummax() - 1.0).min()) if len(curve) else 0.0


def _sharpe(curve: pd.Series) -> float:
    ann = _ann_return(curve)
    vol = _ann_vol(curve)
    return float(ann / vol) if vol > 0 else 0.0


def _metrics(bot: pd.Series, primary: pd.Series, weighted: pd.Series, equal: pd.Series) -> dict[str, float]:
    common = bot.dropna().index.intersection(primary.dropna().index).intersection(weighted.dropna().index).intersection(equal.dropna().index)
    bot = bot.reindex(common)
    primary = primary.reindex(common)
    weighted = weighted.reindex(common)
    equal = equal.reindex(common)

    bot_total = float(bot.iloc[-1] / bot.iloc[0] - 1.0)
    primary_total = float(primary.iloc[-1] / primary.iloc[0] - 1.0)
    weighted_total = float(weighted.iloc[-1] / weighted.iloc[0] - 1.0)
    equal_total = float(equal.iloc[-1] / equal.iloc[0] - 1.0)

    bot_r = _ret(bot)
    primary_r = _ret(primary).reindex(bot_r.index).fillna(0.0)
    weighted_r = _ret(weighted).reindex(bot_r.index).fillna(0.0)
    equal_r = _ret(equal).reindex(bot_r.index).fillna(0.0)

    active_primary = bot_r - primary_r
    active_weighted = bot_r - weighted_r
    active_equal = bot_r - equal_r
    te_primary = float(active_primary.std() * np.sqrt(252)) if len(active_primary) else 0.0
    te_weighted = float(active_weighted.std() * np.sqrt(252)) if len(active_weighted) else 0.0
    te_equal = float(active_equal.std() * np.sqrt(252)) if len(active_equal) else 0.0

    bot_dd = _max_dd(bot)
    primary_dd = _max_dd(primary)
    weighted_dd = _max_dd(weighted)
    equal_dd = _max_dd(equal)

    return {
        "bot_total_return": bot_total,
        "primary_benchmark_total_return": primary_total,
        "weighted_proxy_total_return": weighted_total,
        "equal_weight_total_return": equal_total,
        "alpha_vs_primary": bot_total - primary_total,
        "alpha_vs_weighted_proxy": bot_total - weighted_total,
        "alpha_vs_equal_weight": bot_total - equal_total,
        "bot_annual_return": _ann_return(bot),
        "primary_benchmark_annual_return": _ann_return(primary),
        "weighted_proxy_annual_return": _ann_return(weighted),
        "equal_weight_annual_return": _ann_return(equal),
        "bot_annual_volatility": _ann_vol(bot),
        "primary_benchmark_annual_volatility": _ann_vol(primary),
        "bot_sharpe": _sharpe(bot),
        "primary_benchmark_sharpe": _sharpe(primary),
        "sharpe_spread_vs_primary": _sharpe(bot) - _sharpe(primary),
        "bot_max_drawdown": bot_dd,
        "primary_benchmark_max_drawdown": primary_dd,
        "weighted_proxy_max_drawdown": weighted_dd,
        "equal_weight_max_drawdown": equal_dd,
        "drawdown_reduction_vs_primary": abs(primary_dd) - abs(bot_dd),
        "tracking_error_vs_primary": te_primary,
        "information_ratio_vs_primary": float((active_primary.mean() * 252) / te_primary) if te_primary > 0 else 0.0,
        "tracking_error_vs_weighted": te_weighted,
        "information_ratio_vs_weighted": float((active_weighted.mean() * 252) / te_weighted) if te_weighted > 0 else 0.0,
        "tracking_error_vs_equal": te_equal,
        "information_ratio_vs_equal": float((active_equal.mean() * 252) / te_equal) if te_equal > 0 else 0.0,
        "bot_final_value": float(bot.iloc[-1]),
        "primary_benchmark_final_value": float(primary.iloc[-1]),
        "weighted_proxy_final_value": float(weighted.iloc[-1]),
        "equal_weight_final_value": float(equal.iloc[-1]),
    }


def _slice_for_metrics(curve: pd.Series, metric_start_date: str | None) -> pd.Series:
    clean = curve.dropna()
    if metric_start_date is None or clean.empty:
        return clean
    sliced = clean.loc[clean.index >= pd.Timestamp(metric_start_date)]
    return sliced if len(sliced) >= 2 else clean


def _final_portfolio(weights: pd.Series, scores: pd.DataFrame, assets: list[Asset]) -> pd.DataFrame:
    asset_map = {a.ticker: a for a in assets}
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
    rows.append({"ticker": "CASH", "name": "Caixa/CDI proxy", "sector": "Caixa", "weight": cash, "weight_pct": cash * 100.0, "score": np.nan})
    return pd.DataFrame(rows)


def _should_weekly_rebalance(current_weights: pd.Series, target_weights: pd.Series, current_regime: str | None, new_regime: str, config: dict) -> bool:
    rebalance_cfg = config.get("rebalance", {})
    if not bool(rebalance_cfg.get("weekly_rebalance", True)):
        return False
    current_exposure = float(current_weights.sum())
    target_exposure = float(target_weights.sum())
    exposure_gap = abs(target_exposure - current_exposure)
    min_gap = float(rebalance_cfg.get("weekly_rebalance_min_exposure_gap", 0.08))
    if exposure_gap >= min_gap:
        return True
    if bool(rebalance_cfg.get("weekly_rebalance_on_regime_change", True)) and current_regime is not None and current_regime != new_regime:
        return True
    return False


def _record_row(date: pd.Timestamp, weights: pd.Series, regime_name: str, regime_exposure: float, turnover: float, action: str, prices_columns: pd.Index) -> dict[str, float | str]:
    row: dict[str, float | str] = {ticker: float(weights.get(ticker, 0.0)) for ticker in prices_columns}
    row.update({
        "CASH": max(0.0, 1.0 - float(weights.sum())),
        "REGIME": regime_name,
        "EQUITY_EXPOSURE": float(regime_exposure),
        "TURNOVER": float(turnover),
        "ACTION": action,
        "DATE": str(date.date()),
    })
    return row


def run_backtest_v4(prices: pd.DataFrame, assets: list[Asset], config: dict, benchmark_csv: str | None = None, strict_real_benchmark: bool | None = None, start_date: str | None = None, end_date: str | None = None) -> BacktestV4Result:
    warmup = int(config.get("data", {}).get("min_history_days", 252))
    prices = filter_by_date(prices, start_date=start_date, end_date=end_date, warmup_days=warmup)
    trade_start_date = prices.attrs.get("trade_start_date") or (str(prices.index[warmup].date()) if len(prices) > warmup else None)
    prices = prices.dropna(axis=1, how="all").ffill().dropna(how="all")
    available_assets = [a for a in assets if a.ticker in prices.columns]
    if len(prices) < warmup + 10:
        raise ValueError("Histórico insuficiente para backtest V4 com warmup")

    curves = build_benchmark_curves(prices, available_assets, config, benchmark_csv=benchmark_csv, strict_real_benchmark=strict_real_benchmark)
    primary = curves["primary"]
    weighted = curves["weighted_UTIL_proxy"]
    equal = curves["equal_weight_UTIL"]
    primary_name = primary.name or "primary_benchmark"

    returns = prices.pct_change(fill_method=None).fillna(0.0)
    initial_cash = float(config.get("backtest", {}).get("initial_cash", 10000))
    cost = float(config.get("execution", {}).get("estimated_cost_per_trade", 0.002))
    min_change = float(config.get("rebalance", {}).get("min_weight_change_to_trade", 0.010))

    weights = pd.Series(0.0, index=prices.columns, dtype=float)
    equity = pd.Series(index=prices.index, dtype=float)
    equity.iloc[0] = initial_cash
    rows: list[dict[str, float | str]] = []
    last_scores = pd.DataFrame(index=prices.columns)
    last_regime: str | None = None

    monthly_dates = set(monthly_rebalance_dates(prices.index, trade_start_date=trade_start_date))
    weekly_dates = set(weekly_check_dates(prices.index, trade_start_date=trade_start_date))

    for i, date in enumerate(prices.index[1:], start=1):
        day_ret = float((weights.reindex(returns.columns).fillna(0.0) * returns.loc[date]).sum())
        equity.iloc[i] = equity.iloc[i - 1] * (1.0 + day_ret)

        is_monthly = date in monthly_dates
        is_weekly = date in weekly_dates
        if not is_monthly and not is_weekly:
            continue

        history = prices.loc[:date]
        if len(history) < warmup:
            continue

        benchmark_history = primary.loc[:date]
        regime = detect_regime(history, config, benchmark=benchmark_history)
        last_scores = final_scores(history, config, benchmark=benchmark_history)
        target = build_target_weights_v4(last_scores, history, available_assets, regime, config).reindex(prices.columns).fillna(0.0)

        action = "HOLD"
        should_trade = False
        if is_monthly:
            should_trade = True
            action = "MONTHLY_REBALANCE"
        elif is_weekly and _should_weekly_rebalance(weights, target, last_regime, regime.regime, config):
            should_trade = True
            action = "WEEKLY_RISK_REBALANCE"

        turnover = float((target - weights).abs().sum()) if should_trade else 0.0
        if should_trade and turnover >= min_change:
            equity.iloc[i] *= 1.0 - turnover * cost
            weights = target
        elif should_trade:
            action = "SKIP_SMALL_TURNOVER"

        if should_trade:
            rows.append(_record_row(date, weights, regime.regime, regime.equity_exposure, turnover, action, prices.columns))
            last_regime = regime.regime

    weights_with_cash = weights.copy()
    weights_with_cash.loc["CASH"] = max(0.0, 1.0 - float(weights.sum()))
    final_portfolio = _final_portfolio(weights_with_cash, last_scores, available_assets)
    weights_history = pd.DataFrame(rows).set_index("DATE") if rows else pd.DataFrame()

    metrics = _metrics(
        _slice_for_metrics(equity, trade_start_date),
        _slice_for_metrics(primary, trade_start_date),
        _slice_for_metrics(weighted, trade_start_date),
        _slice_for_metrics(equal, trade_start_date),
    )

    return BacktestV4Result(equity, primary, weighted, equal, weights_history, final_portfolio, metrics, primary_name)


def save_backtest_v4(result: BacktestV4Result, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result.equity_curve.to_csv(out / "equity_curve_v4.csv", header=["bot"])
    result.primary_benchmark_curve.to_csv(out / "benchmark_primary_v4.csv", header=[result.primary_benchmark_name])
    result.weighted_benchmark_curve.to_csv(out / "benchmark_weighted_proxy_v4.csv", header=["weighted_UTIL_proxy"])
    result.equal_weight_benchmark_curve.to_csv(out / "benchmark_equal_weight_v4.csv", header=["equal_weight_UTIL"])
    result.weights_history.to_csv(out / "weights_history_v4.csv")
    result.final_portfolio.to_csv(out / "final_portfolio_v4.csv", index=False)
    pd.DataFrame({"metric": list(result.metrics.keys()), "value": list(result.metrics.values())}).to_csv(out / "metrics_v4.csv", index=False)
    pd.concat([
        result.equity_curve.rename("bot"),
        result.primary_benchmark_curve.rename(result.primary_benchmark_name),
        result.weighted_benchmark_curve.rename("weighted_UTIL_proxy"),
        result.equal_weight_benchmark_curve.rename("equal_weight_UTIL"),
    ], axis=1).to_csv(out / "comparison_curves_v4.csv")
    return out
