import numpy as np
import pandas as pd

from tradebot_util.scoring import final_scores


def make_prices():
    rng = np.random.default_rng(123)
    dates = pd.bdate_range("2020-01-01", periods=320)
    data = {}
    for i, ticker in enumerate(["AAA3", "BBB3", "CCC3", "DDD3", "EEE3"]):
        drift = 0.0002 + i * 0.0001
        rets = rng.normal(drift, 0.01, len(dates))
        data[ticker] = 10 * (1 + pd.Series(rets, index=dates)).cumprod()
    return pd.DataFrame(data)


def test_final_scores_shape_and_range():
    prices = make_prices()
    config = {"score_weights": {"relative_momentum": 0.35, "absolute_momentum": 0.20, "quality": 0.15, "risk": 0.15, "dividends": 0.10, "liquidity": 0.05}}
    scores = final_scores(prices, config)
    assert "score" in scores.columns
    assert len(scores) == prices.shape[1]
    assert scores["score"].between(0, 100).all()
