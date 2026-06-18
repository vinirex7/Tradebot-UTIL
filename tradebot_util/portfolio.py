from __future__ import annotations

import numpy as np
import pandas as pd

from .universe import Asset


def _normalize(weights: pd.Series, target_sum: float) -> pd.Series:
    weights = weights.clip(lower=0.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    total = float(weights.sum())
    if total <= 0:
        return weights
    return weights / total * target_sum


def build_target_weights(scores: pd.DataFrame, assets: list[Asset], equity_exposure: float, config: dict) -> pd.Series:
    portfolio_cfg = config.get("portfolio", {})
    buy_cfg = config.get("buy_rules", {})

    max_positions = int(portfolio_cfg.get("max_positions", 10))
    min_positions = int(portfolio_cfg.get("min_positions", 5))
    min_weight = float(portfolio_cfg.get("min_weight_per_asset", 0.03))
    max_weight = float(portfolio_cfg.get("max_weight_per_asset", 0.18))
    active_tilt_strength = float(portfolio_cfg.get("active_tilt_strength", 0.75))
    min_score_to_buy = float(buy_cfg.get("min_score_to_buy", 65))

    tickers = [asset.ticker for asset in assets]
    base_weights = pd.Series({asset.ticker: asset.index_weight for asset in assets}, dtype=float)
    score = scores["score"].reindex(tickers).fillna(0.0)

    eligible = score[score >= min_score_to_buy].sort_values(ascending=False).head(max_positions)
    if eligible.empty:
        eligible = score.sort_values(ascending=False).head(max(1, min(max_positions, len(score))))

    score_mean = float(score.mean())
    score_std = float(score.std(ddof=0)) or 1.0
    tilt = ((score - score_mean) / score_std).clip(-1.0, 1.0)

    prelim = base_weights * (1.0 + active_tilt_strength * tilt)
    prelim = prelim.reindex(eligible.index).clip(lower=0.0, upper=max_weight)
    weights = _normalize(prelim, equity_exposure)

    for _ in range(10):
        over = weights > max_weight
        if not over.any():
            break
        excess = float((weights[over] - max_weight).sum())
        weights[over] = max_weight
        under = weights[~over]
        if under.empty or excess <= 0:
            break
        weights.loc[under.index] += _normalize(under, excess)

    weights = weights[weights >= min_weight]
    weights = _normalize(weights, equity_exposure)

    if len(weights) < min_positions:
        candidates = score.sort_values(ascending=False).head(min_positions)
        weights = _normalize(base_weights.reindex(candidates.index).fillna(1.0), equity_exposure)
        weights = weights.clip(upper=max_weight)
        weights = _normalize(weights, equity_exposure)

    return weights.sort_values(ascending=False)


def generate_rebalance_orders(current_weights: pd.Series, target_weights: pd.Series, min_change: float = 0.015) -> pd.DataFrame:
    all_tickers = sorted(set(current_weights.index).union(target_weights.index))
    current = current_weights.reindex(all_tickers).fillna(0.0)
    target = target_weights.reindex(all_tickers).fillna(0.0)
    delta = target - current
    orders = pd.DataFrame({"current_weight": current, "target_weight": target, "delta": delta})
    orders = orders[orders["delta"].abs() >= min_change]
    orders["side"] = np.where(orders["delta"] > 0, "BUY", "SELL")
    return orders.sort_values("delta", ascending=False)
