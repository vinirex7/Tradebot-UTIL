from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .indicators import drawdown, equal_weight_index, moving_average


@dataclass(frozen=True)
class RegimeResult:
    regime: str
    equity_exposure: float
    details: dict[str, float | bool | str]


def _last_value(series: pd.Series, default: float = 0.0) -> float:
    clean = series.replace([float("inf"), float("-inf")], pd.NA).dropna()
    return float(clean.iloc[-1]) if len(clean) else default


def _bench_return(benchmark: pd.Series, window: int) -> float:
    if len(benchmark) <= window or benchmark.iloc[-window - 1] <= 0:
        return 0.0
    return float(benchmark.iloc[-1] / benchmark.iloc[-window - 1] - 1.0)


def detect_regime(prices: pd.DataFrame, config: dict[str, Any], benchmark: pd.Series | None = None) -> RegimeResult:
    """Detecta o regime do UTIL usando tendência, momentum, breadth e drawdown.

    V5.3 ficou mais defensivo que a V5.2 porque o backtest mostrou que o bot
    acompanhava o drawdown do UTIL quase de perto. A ideia é continuar comprado
    quando o setor está saudável, mas cortar beta quando o próprio benchmark
    perde tendência/momentum.
    """
    regime_cfg = config.get("regime", {})
    ma_fast = int(regime_cfg.get("ma_fast", 50))
    ma_mid = int(regime_cfg.get("ma_mid", 100))
    ma_slow = int(regime_cfg.get("ma_slow", 200))

    if benchmark is None:
        benchmark = equal_weight_index(prices)

    benchmark = benchmark.reindex(prices.index).ffill().dropna()
    if len(benchmark) < ma_slow + 1:
        return RegimeResult("NEUTRAL", float(regime_cfg.get("neutral_equity", 0.80)), {"reason": "insufficient history"})

    bench_frame = benchmark.to_frame("bench")
    bench_price = float(benchmark.iloc[-1])
    bench_ma_fast = float(moving_average(bench_frame, ma_fast).iloc[-1, 0])
    bench_ma_slow = float(moving_average(bench_frame, ma_slow).iloc[-1, 0])
    bench_ret_21 = _bench_return(benchmark, 21)
    bench_ret_63 = _bench_return(benchmark, 63)
    bench_ret_126 = _bench_return(benchmark, 126)
    bench_drawdown_126 = _last_value(drawdown(bench_frame, 126).iloc[:, 0], 0.0)

    ma100 = moving_average(prices, ma_mid).iloc[-1]
    ma200 = moving_average(prices, ma_slow).iloc[-1]
    latest_prices = prices.iloc[-1]

    breadth_ma100 = float((latest_prices > ma100).mean())
    breadth_ma200 = float((latest_prices > ma200).mean())
    above_slow = bench_price > bench_ma_slow
    fast_above_slow = bench_ma_fast > bench_ma_slow
    momentum_positive = bench_ret_63 > float(regime_cfg.get("risk_on_min_return_3m", 0.00))
    momentum_negative = bench_ret_63 < float(regime_cfg.get("defensive_return_3m", -0.03))

    severe_drawdown = bench_drawdown_126 <= -float(regime_cfg.get("risk_off_benchmark_drawdown", 0.12))
    severe_momentum = bench_ret_63 <= -float(regime_cfg.get("risk_off_return_3m", 0.08))
    short_term_break = bench_ret_21 <= -float(regime_cfg.get("risk_off_return_1m", 0.05))
    breadth_weak = breadth_ma100 <= float(regime_cfg.get("breadth_risk_off", 0.35))

    if (severe_drawdown and (not above_slow or severe_momentum)) or (short_term_break and breadth_weak):
        regime = "RISK_OFF"
        exposure = float(regime_cfg.get("risk_off_equity", 0.30))
    elif (not above_slow) or momentum_negative or breadth_ma100 < float(regime_cfg.get("breadth_neutral", 0.45)):
        regime = "DEFENSIVE"
        exposure = float(regime_cfg.get("defensive_equity", 0.55))
    elif above_slow and fast_above_slow and momentum_positive and breadth_ma100 >= float(regime_cfg.get("breadth_risk_on", 0.60)):
        regime = "RISK_ON"
        exposure = float(regime_cfg.get("risk_on_equity", 0.95))
    else:
        regime = "NEUTRAL"
        exposure = float(regime_cfg.get("neutral_equity", 0.80))

    # Taper adicional: evita ficar com beta alto quando o benchmark está no meio
    # de uma correção, mesmo antes de virar RISK_OFF formal.
    dd_taper_1 = float(regime_cfg.get("drawdown_taper_1", 0.08))
    dd_taper_2 = float(regime_cfg.get("drawdown_taper_2", 0.14))
    if bench_drawdown_126 <= -dd_taper_2:
        exposure *= float(regime_cfg.get("drawdown_taper_2_multiplier", 0.70))
    elif bench_drawdown_126 <= -dd_taper_1:
        exposure *= float(regime_cfg.get("drawdown_taper_1_multiplier", 0.85))

    if bench_ret_126 < 0 and regime in {"NEUTRAL", "DEFENSIVE"}:
        exposure *= float(regime_cfg.get("negative_6m_multiplier", 0.90))

    return RegimeResult(regime, max(0.0, min(1.0, exposure)), {
        "bench_price": bench_price,
        "bench_ma_fast": bench_ma_fast,
        "bench_ma_slow": bench_ma_slow,
        "bench_ret_21": bench_ret_21,
        "bench_ret_63": bench_ret_63,
        "bench_ret_126": bench_ret_126,
        "bench_drawdown_126": bench_drawdown_126,
        "breadth_ma100": breadth_ma100,
        "breadth_ma200": breadth_ma200,
        "above_slow": above_slow,
        "fast_above_slow": fast_above_slow,
        "momentum_positive": momentum_positive,
        "momentum_negative": momentum_negative,
        "severe_drawdown": severe_drawdown,
        "severe_momentum": severe_momentum,
    })
