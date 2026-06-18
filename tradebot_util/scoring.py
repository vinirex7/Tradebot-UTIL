from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .indicators import latest_indicators, rolling_return, rolling_volatility


def _rank_0_100(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    clean = series.replace([np.inf, -np.inf], np.nan)
    if clean.dropna().empty:
        return pd.Series(50.0, index=series.index)
    ranked = clean.rank(pct=True, ascending=not higher_is_better) * 100.0
    return ranked.fillna(50.0)


def relative_momentum_score(prices: pd.DataFrame) -> pd.Series:
    r3 = rolling_return(prices, 63).iloc[-1]
    r6 = rolling_return(prices, 126).iloc[-1]
    r12 = rolling_return(prices, 252).iloc[-1]
    v3 = rolling_volatility(prices, 63).iloc[-1].replace(0, np.nan)
    v6 = rolling_volatility(prices, 126).iloc[-1].replace(0, np.nan)
    v12 = rolling_volatility(prices, 252).iloc[-1].replace(0, np.nan)

    composite = 0.20 * (r3 / v3) + 0.50 * (r6 / v6) + 0.30 * (r12 / v12)
    return _rank_0_100(composite, higher_is_better=True)


def absolute_momentum_score(prices: pd.DataFrame) -> pd.Series:
    ind = latest_indicators(prices)
    score = pd.Series(0.0, index=prices.columns)
    score += (ind["price"] > ind["ma_200"]).astype(float) * 30.0
    score += (ind["ma_50"] > ind["ma_200"]).astype(float) * 25.0
    score += (ind["ret_126"] > 0).astype(float) * 20.0
    score += (ind["ret_252"] > 0).astype(float) * 15.0
    score += (ind["price"] > ind["ma_100"]).astype(float) * 10.0
    return score.clip(0, 100).fillna(0.0)


def risk_score(prices: pd.DataFrame) -> pd.Series:
    ind = latest_indicators(prices)
    vol_component = _rank_0_100(ind["vol_63"], higher_is_better=False)
    dd_component = _rank_0_100(ind["drawdown_126"].abs(), higher_is_better=False)
    return (0.60 * vol_component + 0.40 * dd_component).clip(0, 100)


def liquidity_score(volume: pd.DataFrame | None, prices: pd.DataFrame) -> pd.Series:
    if volume is None or volume.empty:
        return pd.Series(50.0, index=prices.columns)
    aligned_volume = volume.reindex(prices.index).ffill()
    financial_volume = aligned_volume * prices
    avg_volume = financial_volume.rolling(21).mean().iloc[-1]
    return _rank_0_100(avg_volume, higher_is_better=True)


def neutral_score(prices: pd.DataFrame, value: float = 50.0) -> pd.Series:
    return pd.Series(value, index=prices.columns)


def final_scores(
    prices: pd.DataFrame,
    config: dict[str, Any],
    volume: pd.DataFrame | None = None,
    quality: pd.Series | None = None,
    dividends: pd.Series | None = None,
) -> pd.DataFrame:
    weights = config.get("score_weights", {})

    rel = relative_momentum_score(prices)
    abs_mom = absolute_momentum_score(prices)
    risk = risk_score(prices)
    liq = liquidity_score(volume, prices)
    quality_score = quality.reindex(prices.columns).fillna(50.0) if quality is not None else neutral_score(prices)
    dividend_score = dividends.reindex(prices.columns).fillna(50.0) if dividends is not None else neutral_score(prices)

    total = (
        float(weights.get("relative_momentum", 0.35)) * rel
        + float(weights.get("absolute_momentum", 0.20)) * abs_mom
        + float(weights.get("quality", 0.15)) * quality_score
        + float(weights.get("risk", 0.15)) * risk
        + float(weights.get("dividends", 0.10)) * dividend_score
        + float(weights.get("liquidity", 0.05)) * liq
    )

    return pd.DataFrame({
        "relative_momentum": rel,
        "absolute_momentum": abs_mom,
        "quality": quality_score,
        "risk": risk,
        "dividends": dividend_score,
        "liquidity": liq,
        "score": total.clip(0, 100),
    }).sort_values("score", ascending=False)
