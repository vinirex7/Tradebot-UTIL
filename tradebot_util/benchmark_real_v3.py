from __future__ import annotations

from pathlib import Path

import pandas as pd

from .benchmarks_v2 import equal_weight_util_curve, weighted_util_proxy_curve
from .universe import Asset

DATE_CANDIDATES = ["date", "data", "Date", "Data", "DATA"]
VALUE_CANDIDATES = ["close", "Close", "fechamento", "Fechamento", "pontuacao", "Pontuacao", "pontos", "Pontos", "ultimo", "Último", "Ultimo", "last", "Last"]


def _parse_decimal_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = series.astype(str).str.strip()
    cleaned = cleaned.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def _parse_dates(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    iso_mask = text.str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)
    if bool(iso_mask.all()):
        return pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
    br_mask = text.str.match(r"^\d{2}[./-]\d{2}[./-]\d{4}$", na=False)
    if bool(br_mask.all()):
        normalized = text.str.replace(".", "/", regex=False).str.replace("-", "/", regex=False)
        return pd.to_datetime(normalized, format="%d/%m/%Y", errors="coerce")
    return pd.to_datetime(text, dayfirst=True, errors="coerce")


def load_real_util_csv(path: str | Path, initial_cash: float = 10000.0) -> pd.Series:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Benchmark CSV não encontrado: {csv_path}")

    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"Benchmark CSV vazio: {csv_path}")

    date_col = next((col for col in DATE_CANDIDATES if col in df.columns), None)
    value_col = next((col for col in VALUE_CANDIDATES if col in df.columns), None)

    if date_col is None:
        date_col = df.columns[0]
    if value_col is None:
        value_col = df.columns[1] if len(df.columns) > 1 else None
    if value_col is None:
        raise ValueError("CSV do benchmark precisa ter uma coluna de data e uma coluna de valor")

    dates = _parse_dates(df[date_col])
    values = _parse_decimal_series(df[value_col])
    series = pd.Series(values.values, index=dates).dropna().sort_index()
    series = series[~series.index.duplicated(keep="last")]

    if len(series) < 2:
        raise ValueError("Série do UTIL real tem dados insuficientes")
    if float(series.iloc[0]) <= 0:
        raise ValueError("Primeiro valor do benchmark precisa ser maior que zero")

    curve = initial_cash * (series / float(series.iloc[0]))
    curve.name = "real_UTIL_csv"
    return curve


def build_benchmark_curves(prices: pd.DataFrame, assets: list[Asset], config: dict, benchmark_csv: str | None = None, strict_real_benchmark: bool | None = None) -> dict[str, pd.Series]:
    initial_cash = float(config.get("backtest", {}).get("initial_cash", 10000))
    benchmark_cfg = config.get("benchmark", {})
    csv_path = benchmark_csv or benchmark_cfg.get("csv_path")
    strict = bool(benchmark_cfg.get("strict_real_benchmark", False)) if strict_real_benchmark is None else strict_real_benchmark

    curves: dict[str, pd.Series] = {
        "weighted_UTIL_proxy": weighted_util_proxy_curve(prices, assets, initial_cash),
        "equal_weight_UTIL": equal_weight_util_curve(prices, initial_cash),
    }

    try:
        real_curve = load_real_util_csv(csv_path, initial_cash=initial_cash)
        real_curve = real_curve.reindex(prices.index).ffill().dropna()
        curves["real_UTIL_csv"] = real_curve
        curves["primary"] = real_curve
    except Exception:
        if strict:
            raise
        curves["primary"] = curves["weighted_UTIL_proxy"]

    return curves
