import numpy as np
import pandas as pd

from tradebot_util.backtest_v3 import run_backtest_v3
from tradebot_util.benchmark_real_v3 import load_real_util_csv
from tradebot_util.universe import Asset


def make_prices():
    rng = np.random.default_rng(777)
    dates = pd.bdate_range("2020-01-01", periods=420)
    data = {}
    for i, ticker in enumerate(["AAA3", "BBB3", "CCC3", "DDD3", "EEE3", "FFF3"]):
        drift = 0.0002 + i * 0.00004
        vol = 0.010 + (i % 3) * 0.002
        rets = rng.normal(drift, vol, len(dates))
        data[ticker] = 10 * (1 + pd.Series(rets, index=dates)).cumprod()
    return pd.DataFrame(data)


def make_assets():
    weights = [0.30, 0.25, 0.20, 0.10, 0.10, 0.05]
    return [Asset(ticker, ticker, "Energia Elétrica", weight) for ticker, weight in zip(["AAA3", "BBB3", "CCC3", "DDD3", "EEE3", "FFF3"], weights)]


def make_config():
    return {
        "data": {"min_history_days": 252},
        "benchmark": {"strict_real_benchmark": False, "csv_path": "missing.csv"},
        "regime": {"risk_on_equity": 1.0, "neutral_equity": 0.92, "defensive_equity": 0.62, "risk_off_equity": 0.25, "ma_fast": 50, "ma_mid": 100, "ma_slow": 200, "breadth_risk_on": 0.55, "breadth_neutral": 0.40, "breadth_risk_off": 0.30},
        "portfolio_v3": {"min_positions": 3, "max_positions": 6, "min_weight_per_asset": 0.01, "max_weight_per_asset": 0.40, "score_power": 1.4, "use_inverse_volatility": True, "volatility_window": 63, "target_volatility": 0.18, "min_equity_exposure": 0.25, "max_equity_exposure": 1.0},
        "score_weights": {"relative_momentum": 0.50, "absolute_momentum": 0.25, "quality": 0.03, "risk": 0.17, "dividends": 0.02, "liquidity": 0.03},
        "buy_rules": {"min_score_to_buy": 50, "allow_top_rank_exception": True, "top_rank_exception_count": 4},
        "rebalance": {"min_weight_change_to_trade": 0.01},
        "execution": {"estimated_cost_per_trade": 0.002},
        "backtest": {"initial_cash": 10000},
    }


def test_load_real_util_csv(tmp_path):
    path = tmp_path / "util.csv"
    path.write_text("date,close\n2020-01-01,1000\n2020-01-02,1100\n", encoding="utf-8")
    curve = load_real_util_csv(path, initial_cash=10000)
    assert curve.name == "real_UTIL_csv"
    assert curve.iloc[-1] == 11000


def test_backtest_v3_runs_with_proxy_fallback():
    prices = make_prices()
    result = run_backtest_v3(prices, make_assets(), make_config())
    assert "bot_total_return" in result.metrics
    assert "primary_benchmark_total_return" in result.metrics
    assert not result.final_portfolio.empty
    assert result.primary_benchmark_name in {"weighted_UTIL_proxy", "real_UTIL_csv"}


def test_backtest_v3_date_window():
    prices = make_prices()
    result = run_backtest_v3(prices, make_assets(), make_config(), start_date="2021-01-01")
    assert len(result.equity_curve.dropna()) > 0
    assert "alpha_vs_primary" in result.metrics
