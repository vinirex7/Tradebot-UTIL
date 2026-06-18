from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .benchmark_real_v3 import load_real_util_csv
from .config import load_config
from .market_data import download_adjusted_close, download_volume
from .portfolio_v4 import build_target_weights_v4
from .regime import detect_regime
from .scoring import final_scores
from .universe import tickers
from .universe_dynamic_v5 import load_active_universe_or_config, update_dynamic_universe


@dataclass(frozen=True)
class LiveDecisionV5:
    as_of: str
    regime: str
    equity_exposure: float
    target_weights: pd.Series
    scores: pd.DataFrame
    benchmark_used: str
    universe_size: int


def load_live_prices(config: dict[str, Any], tickers_list: list[str], prices_csv: str | None = None) -> pd.DataFrame:
    if prices_csv:
        prices = pd.read_csv(prices_csv, index_col=0, parse_dates=True)
        cols = [ticker for ticker in tickers_list if ticker in prices.columns]
        if not cols:
            raise ValueError("Nenhum ticker do universo encontrado no CSV de preços")
        return prices[cols].dropna(how="all").sort_index()
    start = config.get("data", {}).get("start", "2018-01-01")
    return download_adjusted_close(tickers_list, start=start, auto_adjust=True)


def load_live_benchmark(config: dict[str, Any], prices: pd.DataFrame, benchmark_csv: str | None = None) -> tuple[pd.Series | None, str]:
    benchmark_cfg = config.get("benchmark", {})
    csv_path = benchmark_csv or benchmark_cfg.get("csv_path")
    if not csv_path:
        return None, "equal_weight_fallback"
    try:
        benchmark = load_real_util_csv(csv_path, initial_cash=10000.0)
        benchmark = benchmark.reindex(prices.index).ffill().dropna()
        if len(benchmark) >= 2:
            return benchmark, "real_UTIL_csv"
    except Exception:
        if bool(benchmark_cfg.get("strict_real_benchmark", False)):
            raise
    return None, "equal_weight_fallback"


def generate_live_decision_v5(
    config_path: str = "config_v5.yaml",
    benchmark_csv: str | None = None,
    universe_csv: str | None = None,
    prices_csv: str | None = None,
    update_universe_first: bool = False,
) -> LiveDecisionV5:
    config = load_config(config_path)
    if update_universe_first:
        update_dynamic_universe(config, source_csv=universe_csv)

    assets = load_active_universe_or_config(config)
    tickers_list = tickers(assets)
    prices = load_live_prices(config, tickers_list, prices_csv=prices_csv)
    volume = None
    if prices_csv is None:
        try:
            volume = download_volume(list(prices.columns), start=config.get("data", {}).get("start", "2018-01-01"))
        except Exception:
            volume = None

    benchmark, benchmark_name = load_live_benchmark(config, prices, benchmark_csv=benchmark_csv)
    regime = detect_regime(prices, config, benchmark=benchmark)
    scores = final_scores(prices, config, volume=volume)
    target = build_target_weights_v4(scores, prices, assets, regime, config)

    return LiveDecisionV5(
        as_of=str(prices.index[-1].date()),
        regime=regime.regime,
        equity_exposure=float(regime.equity_exposure),
        target_weights=target.sort_values(ascending=False),
        scores=scores.sort_values("score", ascending=False),
        benchmark_used=benchmark_name,
        universe_size=len(assets),
    )


def save_live_decision(decision: LiveDecisionV5, output_dir: str | Path = "state/live") -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    target = decision.target_weights.copy()
    target.loc["CASH"] = max(0.0, 1.0 - float(target.sum()))
    target.to_csv(out / "target_weights.csv", header=["weight"])
    decision.scores.to_csv(out / "scores.csv")
    summary = pd.DataFrame([
        {"field": "as_of", "value": decision.as_of},
        {"field": "regime", "value": decision.regime},
        {"field": "equity_exposure", "value": decision.equity_exposure},
        {"field": "benchmark_used", "value": decision.benchmark_used},
        {"field": "universe_size", "value": decision.universe_size},
    ])
    summary.to_csv(out / "decision_summary.csv", index=False)
    return out
