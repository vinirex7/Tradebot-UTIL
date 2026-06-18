import numpy as np
import pandas as pd

from tradebot_util.backtest_v4 import run_backtest_v4, weekly_check_dates
from tradebot_util.portfolio_v4 import build_target_weights_v4
from tradebot_util.regime import RegimeResult
from tradebot_util.scoring import final_scores
from tradebot_util.universe import Asset


def make_prices():
    rng = np.random.default_rng(444)
    dates = pd.bdate_range("2020-01-01", periods=430)
    data = {}
    for i, ticker in enumerate(["AAA3", "BBB3", "CCC3", "DDD3", "EEE3", "FFF3"]):
        drift = 0.00025 + i * 0.00004
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
        "regime": {"risk_on_equity": 1.0, "neutral_equity": 0.98, "defensive_equity": 0.78, "risk_off_equity": 0.45, "ma_fast": 50, "ma_mid": 100, "ma_slow": 200, "breadth_risk_on": 0.55, "breadth_neutral": 0.40, "breadth_risk_off": 0.30},
        "portfolio_v4": {"min_positions": 3, "max_positions": 6, "min_weight_per_asset": 0.01, "max_weight_per_asset": 0.40, "max_top3_weight": 0.85, "score_power": 1.5, "use_inverse_volatility": True, "volatility_window": 63, "target_volatility": 0.24, "apply_vol_target_only_in_defense": True, "vol_scalar_floor": 0.65, "max_cash_by_regime": {"RISK_ON": 0.05, "NEUTRAL": 0.10, "DEFENSIVE": 0.28, "RISK_OFF": 0.55}, "min_equity_exposure": 0.35, "max_equity_exposure": 1.0},
        "score_weights": {"relative_momentum": 0.52, "absolute_momentum": 0.26, "quality": 0.02, "risk": 0.15, "dividends": 0.02, "liquidity": 0.03},
        "buy_rules": {"min_score_to_buy": 50, "allow_top_rank_exception": True, "top_rank_exception_count": 4},
        "rebalance": {"min_weight_change_to_trade": 0.01, "weekly_rebalance": True, "weekly_rebalance_min_exposure_gap": 0.08, "weekly_rebalance_on_regime_change": True},
        "execution": {"estimated_cost_per_trade": 0.002},
        "backtest": {"initial_cash": 10000},
    }


def test_weekly_check_dates_are_created():
    dates = pd.bdate_range("2024-01-01", periods=60)
    checks = weekly_check_dates(dates, trade_start_date="2024-01-15")
    assert len(checks) >= 8
    assert checks.min() >= pd.Timestamp("2024-01-15")


def test_portfolio_v4_respects_regime_cash_limit():
    prices = make_prices()
    scores = final_scores(prices, make_config())
    regime = RegimeResult("RISK_ON", 1.0, {})
    weights = build_target_weights_v4(scores, prices, make_assets(), regime, make_config())
    assert weights.sum() >= 0.95 - 1e-9
    assert weights.max() <= 0.40 + 1e-9


def test_backtest_v4_runs_with_weekly_rebalance():
    prices = make_prices()
    result = run_backtest_v4(prices, make_assets(), make_config())
    assert "bot_total_return" in result.metrics
    assert "primary_benchmark_total_return" in result.metrics
    assert not result.final_portfolio.empty
    assert not result.weights_history.empty
    assert "ACTION" in result.weights_history.columns
