from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import moving_average, rolling_volatility
from .regime import RegimeResult
from .universe import Asset


def _normalize(weights: pd.Series, target_sum: float) -> pd.Series:
    weights = weights.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(lower=0.0)
    total = float(weights.sum())
    if total <= 0:
        return weights
    return weights / total * target_sum


def _cap_weights(weights: pd.Series, max_weight: float, target_sum: float) -> pd.Series:
    weights = weights.copy().clip(lower=0.0)
    for _ in range(25):
        over = weights > max_weight
        if not over.any():
            break
        excess = float((weights[over] - max_weight).sum())
        weights[over] = max_weight
        under = weights[~over]
        if excess <= 1e-12 or under.empty or float(under.sum()) <= 0:
            break
        weights.loc[under.index] += _normalize(under, excess)
    return _normalize(weights.clip(upper=max_weight), target_sum)


def _cap_top3(weights: pd.Series, max_top3: float, target_sum: float) -> pd.Series:
    weights = weights.sort_values(ascending=False).copy()
    if len(weights) < 4 or float(weights.head(3).sum()) <= max_top3:
        return _normalize(weights, target_sum)

    top = weights.head(3)
    rest = weights.iloc[3:]
    top = _normalize(top, min(max_top3, target_sum))
    rest_target = max(0.0, target_sum - float(top.sum()))
    rest = _normalize(rest, rest_target) if not rest.empty else rest
    return pd.concat([top, rest]).sort_values(ascending=False)


def _portfolio_realized_vol(prices: pd.DataFrame, raw_weights: pd.Series, window: int) -> float:
    returns = prices.pct_change(fill_method=None).dropna()
    common = [ticker for ticker in raw_weights.index if ticker in returns.columns]
    if len(common) < 2:
        return 0.0
    weights = raw_weights.reindex(common).fillna(0.0)
    if float(weights.sum()) <= 0:
        return 0.0
    weights = weights / float(weights.sum())
    port_rets = (returns[common].tail(window) * weights).sum(axis=1)
    return float(port_rets.std() * np.sqrt(252)) if len(port_rets) > 2 else 0.0


def _regime_max_cash(regime: str, config: dict) -> float:
    cfg = config.get("portfolio_v4", {})
    mapping = cfg.get("max_cash_by_regime", {})
    return float(mapping.get(regime, mapping.get(regime.upper(), 0.25)))


def _target_exposure(raw_weights: pd.Series, prices: pd.DataFrame, regime: RegimeResult, config: dict) -> float:
    cfg = config.get("portfolio_v4", {})
    min_exposure = float(cfg.get("min_equity_exposure", 0.35))
    max_exposure = float(cfg.get("max_equity_exposure", 1.00))
    target_vol = float(cfg.get("target_volatility", 0.24))
    vol_window = int(cfg.get("volatility_window", 63))
    scalar_floor = float(cfg.get("vol_scalar_floor", 0.65))
    apply_vol_only_defense = bool(cfg.get("apply_vol_target_only_in_defense", True))

    exposure = float(regime.equity_exposure)
    realized_vol = _portfolio_realized_vol(prices, raw_weights, vol_window)
    if realized_vol > 0 and target_vol > 0:
        should_apply_vol = (not apply_vol_only_defense) or regime.regime in {"DEFENSIVE", "RISK_OFF"}
        if should_apply_vol and realized_vol > target_vol:
            exposure *= max(scalar_floor, target_vol / realized_vol)

    max_cash = _regime_max_cash(regime.regime, config)
    regime_floor = max(0.0, 1.0 - max_cash)
    exposure = max(exposure, regime_floor)
    return max(min_exposure, min(max_exposure, exposure))


def _trend_multiplier(prices: pd.DataFrame, tickers: pd.Index) -> pd.Series:
    price = prices[tickers].iloc[-1]
    ma50 = moving_average(prices[tickers], 50).iloc[-1]
    ma200 = moving_average(prices[tickers], 200).iloc[-1]
    multiplier = pd.Series(1.0, index=tickers)
    multiplier += (price > ma50).astype(float) * 0.10
    multiplier += (ma50 > ma200).astype(float) * 0.15
    multiplier += (price > ma200).astype(float) * 0.10
    return multiplier.fillna(1.0)


def build_target_weights_v4(scores: pd.DataFrame, prices: pd.DataFrame, assets: list[Asset], regime: RegimeResult, config: dict) -> pd.Series:
    cfg = config.get("portfolio_v4", {})
    buy_cfg = config.get("buy_rules", {})

    min_positions = int(cfg.get("min_positions", 5))
    max_positions = int(cfg.get("max_positions", 8))
    min_weight = float(cfg.get("min_weight_per_asset", 0.03))
    max_weight = float(cfg.get("max_weight_per_asset", 0.26))
    max_top3 = float(cfg.get("max_top3_weight", 0.68))
    score_power = float(cfg.get("score_power", 1.75))
    use_inverse_vol = bool(cfg.get("use_inverse_volatility", True))
    vol_window = int(cfg.get("volatility_window", 63))
    min_score = float(buy_cfg.get("min_score_to_buy", 56))
    allow_top_exception = bool(buy_cfg.get("allow_top_rank_exception", True))
    top_exception_count = int(buy_cfg.get("top_rank_exception_count", 5))

    available = [asset.ticker for asset in assets if asset.ticker in prices.columns and asset.ticker in scores.index]
    score = scores["score"].reindex(available).dropna()
    if score.empty:
        return pd.Series(dtype=float)

    eligible = score[score >= min_score].sort_values(ascending=False).head(max_positions)
    if allow_top_exception and len(eligible) < min_positions:
        eligible = score.sort_values(ascending=False).head(min(max_positions, max(min_positions, top_exception_count)))
    if eligible.empty:
        eligible = score.sort_values(ascending=False).head(min_positions)

    score_floor = float(eligible.min())
    score_edge = (eligible - score_floor + 1.0).clip(lower=0.0)
    raw = score_edge ** score_power
    raw *= _trend_multiplier(prices, eligible.index)

    if use_inverse_vol:
        vols = rolling_volatility(prices[eligible.index], vol_window).iloc[-1].replace(0, np.nan)
        inv_vol = 1.0 / vols
        raw *= inv_vol.reindex(eligible.index).fillna(inv_vol.median())

    if float(raw.sum()) <= 0:
        raw = pd.Series(1.0, index=eligible.index)

    raw = _normalize(raw, 1.0)
    final_exposure = _target_exposure(raw, prices, regime, config)
    weights = _normalize(raw, final_exposure)
    weights = _cap_weights(weights, max_weight, final_exposure)
    weights = _cap_top3(weights, max_top3, final_exposure)
    weights = weights[weights >= min_weight]
    weights = _normalize(weights, final_exposure)
    weights = _cap_weights(weights, max_weight, final_exposure)
    weights = _cap_top3(weights, max_top3, final_exposure)
    return weights.sort_values(ascending=False)
