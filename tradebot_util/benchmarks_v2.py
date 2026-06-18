from __future__ import annotations

import pandas as pd

from .indicators import returns
from .universe import Asset


def normalized_index_weights(assets: list[Asset], columns: list[str] | pd.Index) -> pd.Series:
    raw = pd.Series({asset.ticker: asset.index_weight for asset in assets}, dtype=float)
    weights = raw.reindex(columns).fillna(0.0)
    total = float(weights.sum())
    if total <= 0:
        return pd.Series(1.0 / len(columns), index=columns, dtype=float)
    return weights / total


def weighted_util_proxy_curve(prices: pd.DataFrame, assets: list[Asset], initial_cash: float = 10000.0) -> pd.Series:
    weights = normalized_index_weights(assets, prices.columns)
    rets = returns(prices).fillna(0.0)
    bench_rets = (rets * weights).sum(axis=1)
    curve = initial_cash * (1.0 + bench_rets).cumprod()
    curve.name = "weighted_UTIL_proxy"
    return curve


def equal_weight_util_curve(prices: pd.DataFrame, initial_cash: float = 10000.0) -> pd.Series:
    rets = returns(prices).fillna(0.0)
    bench_rets = rets.mean(axis=1)
    curve = initial_cash * (1.0 + bench_rets).cumprod()
    curve.name = "equal_weight_UTIL"
    return curve
