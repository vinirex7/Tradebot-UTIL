import numpy as np
import pandas as pd

from tradebot_util.backtest_v2 import run_backtest_v2
from tradebot_util.benchmarks_v2 import weighted_util_proxy_curve
from tradebot_util.universe import Asset


def make_prices():
    rng = np.random.default_rng(321)
    dates = pd.bdate_range("2020-01-01", periods=360)
    data = {}
    for i, ticker in enumerate(["AAA3", "BBB3", "CCC3", "DDD3", "EEE3", "FFF3"]):
        drift = 0.0002 + i * 0.00005
        vol = 0.010 + (i % 3) * 0.002
        rets = rng.normal(drift, vol, len(dates))
        data[ticker] = 10 * (1 + pd.Series(rets, index=dates)).cumprod()
    return pd.DataFrame(data)


def make_assets():
    weights = [0.30, 0.25, 0.20, 0.10, 0.10, 0.05]
    return [Asset(ticker, ticker, "Energia Elétrica", weight) for ticker, weight in zip(["AAA3", "BBB3", "CCC3", "DDD3", "EEE3", "FFF3"], weights)]


def make_config():
    return {
        "regime": {
            "risk_on_equity": 1.0,
            "neutral_equity": 0.95,
            "defensive_equity": 0.75,
            "risk_off_equity": 0.45,
            "ma_fast": 50,
            "ma_mid": 100,
            "ma_slow": 200,
            "breadth_risk_on": 0.55,
            "breadth_neutral": 0.40,
            "breadth_risk_off": 0.30,
        },
        "portfolio": {
            "min_positions": 3,
            "max_positions": 6,
            "min_weight_per_asset": 0.01,
            "max_weight_per_asset": 0.40,
            "active_tilt_strength": 1.0,
        },
        "score_weights": {
            "relative_momentum": 0.45,
            "absolute_momentum": 0.25,
            "quality": 0.05,
            "risk": 0.15,
            "dividends": 0.05,
            "liquidity": 0.05,
        },
        "buy_rules": {"min_score_to_buy": 50},
        "rebalance": {"min_weight_change_to_trade": 0.01},
        "execution": {"estimated_cost_per_trade": 0.002},
        "backtest": {"initial_cash": 10000},
    }


def test_weighted_benchmark_curve_is_created():
    prices = make_prices()
    assets = make_assets()
    curve = weighted_util_proxy_curve(prices, assets, initial_cash=10000)
    assert len(curve) == len(prices)
    assert curve.iloc[0] > 0
    assert curve.name == "weighted_UTIL_proxy"


def test_backtest_v2_outputs_metrics_and_final_portfolio():
    prices = make_prices()
    assets = make_assets()
    result = run_backtest_v2(prices, assets, make_config())
    assert "bot_total_return" in result.metrics
    assert "weighted_benchmark_total_return" in result.metrics
    assert "alpha_vs_weighted_benchmark" in result.metrics
    assert not result.final_portfolio.empty
    assert "CASH" in set(result.final_portfolio["ticker"])
