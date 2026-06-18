from __future__ import annotations

from typing import Iterable

import pandas as pd
import yfinance as yf


def to_yfinance_ticker(ticker: str) -> str:
    return ticker if ticker.endswith(".SA") else f"{ticker}.SA"


def from_yfinance_ticker(ticker: str) -> str:
    return ticker.replace(".SA", "")


def download_adjusted_close(tickers: Iterable[str], start: str = "2018-01-01", auto_adjust: bool = True) -> pd.DataFrame:
    yf_tickers = [to_yfinance_ticker(t) for t in tickers]
    if not yf_tickers:
        raise ValueError("At least one ticker is required")

    raw = yf.download(yf_tickers, start=start, auto_adjust=auto_adjust, progress=False, group_by="column", threads=True)
    if raw.empty:
        raise ValueError("No market data returned by provider")

    if isinstance(raw.columns, pd.MultiIndex):
        price_field = "Close" if auto_adjust else "Adj Close"
        if price_field not in raw.columns.get_level_values(0):
            price_field = "Adj Close" if "Adj Close" in raw.columns.get_level_values(0) else "Close"
        prices = raw[price_field].copy()
    else:
        prices = raw[["Close"]].copy()
        prices.columns = [yf_tickers[0]]

    prices = prices.rename(columns={col: from_yfinance_ticker(str(col)) for col in prices.columns})
    return prices.dropna(axis=1, how="all").sort_index()


def download_volume(tickers: Iterable[str], start: str = "2018-01-01") -> pd.DataFrame:
    yf_tickers = [to_yfinance_ticker(t) for t in tickers]
    raw = yf.download(yf_tickers, start=start, auto_adjust=False, progress=False, group_by="column", threads=True)
    if raw.empty:
        raise ValueError("No volume data returned by provider")

    if isinstance(raw.columns, pd.MultiIndex):
        volume = raw["Volume"].copy()
    else:
        volume = raw[["Volume"]].copy()
        volume.columns = [yf_tickers[0]]

    volume = volume.rename(columns={col: from_yfinance_ticker(str(col)) for col in volume.columns})
    return volume.sort_index()
