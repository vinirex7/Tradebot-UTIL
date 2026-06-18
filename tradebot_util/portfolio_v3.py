from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import rolling_volatility
from .universe import Asset


def _normalize(weights: pd.Series, target_sum: float) -> pd.Series:
    weights = weights.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(lower=0.0)
    total = float(weights.sum())
    if total <= 0:
        return weights
    return weights / total * target_sum


def _cap_weights(weights: pd.Series, max_weight: float, target_sum: float) -> pd.Series:
    weights = weights.copy()
    for _ in range(20):
        over = weights > max_weight
        if not over.any():
            break
        capped_sum = float(weights[over].sum())
        weights[over] = max_weight
        excess = capped_sum - float(weights[over].sum())
        under = weights[~over]
        if excess <= 1e-12 or under.empty or float(under.sum()) <= 0:
            break
        weights.loc[under.index] += _normalize(under, excess)
    return _normalize(weights.clip(upper=max_weight), target_sum)


def _volatility_scalar(prices: pd.DataFrame, raw_weights: pd.Series, target_vol: float, window: int, min_exposure: float, max_exposure: float) -> float:
    if raw_weights.empty or raw_weights.sum() <= 0:
        return min_exposure
    returns = prices.pct_change(fill_method=None).dropna()
    common = [ticker for ticker in raw_weights.index if ticker in returns.columns]
    if len(common) < 2:
        return max_exposure
    w = raw_weights.reindex(common).fillna(0.0)
    w = w / float(w.sum())
    port_rets = (returns[common].tail(window) * w).sum(axis=1)
    realized_vol = float(port_rets.std() * np.sqrt(252)) if len(port_rets) > 2 else 0.0
    if realized_vol <= 0:
        return max_exposure
    scalar = target_vol / realized_vol
    return max(min_exposure, min(max_exposure, scalar))


def build_target_weights_v3(scores: pd.DataFrame, prices: pd.DataFrame, assets: list[Asset], regime_exposure: float, config: dict) -> pd.Series:
    cfg = config.get("portfolio_v3", {})
    buy_cfg = config.get("buy_rules", {})

    min_positions = int(cfg.get("min_positions", 5))
    max_positions = int(cfg.get("max_positions", 8))
    min_weight = float(cfg.get("min_weight_per_asset", 0.03))
    max_weight = float(cfg.get("max_weight_per_asset", 0.24))
    score_power = float(cfg.get("score_power", 1.60))
    use_inverse_vol = bool(cfg.get("use_inverse_volatility", True))
    vol_window = int(cfg.get("volatility_window", 63))
    target_vol = float(cfg.get("target_volatility", 0.18))
    min_exposure = float(cfg.get("min_equity_exposure", 0.25))
    max_exposure = float(cfg.get("max_equity_exposure", 1.00))
    min_score = float(buy_cfg.get("min_score_to_buy", 58))
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
    score_weight = score_edge ** score_power

    if use_inverse_vol:
        vols = rolling_volatility(prices[eligible.index], vol_window).iloc[-1].replace(0, np.nan)
        inv_vol = 1.0 / vols
        raw = score_weight * inv_vol.reindex(eligible.index).fillna(inv_vol.median())
    else:
        raw = score_weight

    if raw.sum() <= 0:
        raw = pd.Series(1.0, index=eligible.index)

    raw = _normalize(raw, 1.0)
    vol_scalar = _volatility_scalar(prices, raw, target_vol, vol_window, min_exposure, max_exposure)
    final_exposure = max(min_exposure, min(max_exposure, regime_exposure * vol_scalar))

    weights = _normalize(raw, final_exposure)
    weights = _cap_weights(weights, max_weight, final_exposure)
    weights = weights[weights >= min_weight]
    weights = _normalize(weights, final_exposure)
    weights = _cap_weights(weights, max_weight, final_exposure)

    return weights.sort_values(ascending=False)
