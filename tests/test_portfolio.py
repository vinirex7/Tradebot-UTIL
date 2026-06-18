import pandas as pd

from tradebot_util.portfolio import build_target_weights, generate_rebalance_orders
from tradebot_util.universe import Asset


def test_build_target_weights_respects_exposure_and_max_weight():
    assets = [
        Asset("AAA3", "A", "Energia Elétrica", 0.40),
        Asset("BBB3", "B", "Energia Elétrica", 0.25),
        Asset("CCC3", "C", "Água e Saneamento", 0.20),
        Asset("DDD3", "D", "Energia Elétrica", 0.10),
        Asset("EEE3", "E", "Água e Saneamento", 0.05),
    ]
    scores = pd.DataFrame({"score": [90, 80, 70, 66, 30]}, index=[a.ticker for a in assets])
    config = {"portfolio": {"max_positions": 5, "min_positions": 3, "min_weight_per_asset": 0.03, "max_weight_per_asset": 0.35, "active_tilt_strength": 0.75}, "buy_rules": {"min_score_to_buy": 65}}
    weights = build_target_weights(scores, assets, equity_exposure=0.80, config=config)
    assert abs(weights.sum() - 0.80) < 1e-9
    assert weights.max() <= 0.35 + 1e-9
    assert "EEE3" not in weights.index


def test_generate_rebalance_orders_filters_small_changes():
    current = pd.Series({"AAA3": 0.10, "BBB3": 0.20})
    target = pd.Series({"AAA3": 0.11, "BBB3": 0.16, "CCC3": 0.05})
    orders = generate_rebalance_orders(current, target, min_change=0.015)
    assert "AAA3" not in orders.index
    assert set(orders.index) == {"BBB3", "CCC3"}
