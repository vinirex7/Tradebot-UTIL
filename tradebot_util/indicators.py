from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change(fill_method=None)


def rolling_return(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    return prices / prices.shift(window) - 1.0


def rolling_volatility(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    return returns(prices).rolling(window).std() * np.sqrt(TRADING_DAYS)


def moving_average(prices: pd.DataFrame, window: int) -> pd.DataFrame:
    return prices.rolling(window).mean()


def drawdown(prices: pd.DataFrame, window: int | None = None) -> pd.DataFrame:
    peak = prices.cummax() if window is None else prices.rolling(window).max()
    return prices / peak - 1.0


def equal_weight_index(prices: pd.DataFrame) -> pd.Series:
    rets = returns(prices).fillna(0.0)
    return (1.0 + rets.mean(axis=1)).cumprod()


def latest_indicators(prices: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "ret_63": rolling_return(prices, 63).iloc[-1],
        "ret_126": rolling_return(prices, 126).iloc[-1],
        "ret_252": rolling_return(prices, 252).iloc[-1],
        "vol_63": rolling_volatility(prices, 63).iloc[-1],
        "vol_126": rolling_volatility(prices, 126).iloc[-1],
        "ma_20": moving_average(prices, 20).iloc[-1],
        "ma_50": moving_average(prices, 50).iloc[-1],
        "ma_100": moving_average(prices, 100).iloc[-1],
        "ma_200": moving_average(prices, 200).iloc[-1],
        "price": prices.iloc[-1],
        "drawdown_126": drawdown(prices, 126).iloc[-1],
    }
