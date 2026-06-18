from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .indicators import equal_weight_index, moving_average


@dataclass(frozen=True)
class RegimeResult:
    regime: str
    equity_exposure: float
    details: dict[str, float | bool | str]


def detect_regime(prices: pd.DataFrame, config: dict[str, Any], benchmark: pd.Series | None = None) -> RegimeResult:
    regime_cfg = config.get("regime", {})
    ma_fast = int(regime_cfg.get("ma_fast", 50))
    ma_mid = int(regime_cfg.get("ma_mid", 100))
    ma_slow = int(regime_cfg.get("ma_slow", 200))

    if benchmark is None:
        benchmark = equal_weight_index(prices)

    benchmark = benchmark.dropna()
    if len(benchmark) < ma_slow + 1:
        return RegimeResult("NEUTRAL", float(regime_cfg.get("neutral_equity", 0.80)), {"reason": "insufficient history"})

    bench_price = float(benchmark.iloc[-1])
    bench_ma_fast = float(moving_average(benchmark.to_frame("bench"), ma_fast).iloc[-1, 0])
    bench_ma_slow = float(moving_average(benchmark.to_frame("bench"), ma_slow).iloc[-1, 0])

    ma100 = moving_average(prices, ma_mid).iloc[-1]
    ma200 = moving_average(prices, ma_slow).iloc[-1]
    latest_prices = prices.iloc[-1]

    breadth_ma100 = float((latest_prices > ma100).mean())
    breadth_ma200 = float((latest_prices > ma200).mean())
    above_slow = bench_price > bench_ma_slow
    fast_above_slow = bench_ma_fast > bench_ma_slow

    if above_slow and fast_above_slow and breadth_ma100 >= float(regime_cfg.get("breadth_risk_on", 0.60)):
        regime = "RISK_ON"
        exposure = float(regime_cfg.get("risk_on_equity", 0.95))
    elif (not above_slow) and (not fast_above_slow) and breadth_ma100 <= float(regime_cfg.get("breadth_risk_off", 0.35)):
        regime = "RISK_OFF"
        exposure = float(regime_cfg.get("risk_off_equity", 0.30))
    elif breadth_ma100 < float(regime_cfg.get("breadth_neutral", 0.45)) or not above_slow:
        regime = "DEFENSIVE"
        exposure = float(regime_cfg.get("defensive_equity", 0.55))
    else:
        regime = "NEUTRAL"
        exposure = float(regime_cfg.get("neutral_equity", 0.80))

    return RegimeResult(regime, max(0.0, min(1.0, exposure)), {
        "bench_price": bench_price,
        "bench_ma_fast": bench_ma_fast,
        "bench_ma_slow": bench_ma_slow,
        "breadth_ma100": breadth_ma100,
        "breadth_ma200": breadth_ma200,
        "above_slow": above_slow,
        "fast_above_slow": fast_above_slow,
    })
