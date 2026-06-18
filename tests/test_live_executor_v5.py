import pandas as pd

from tradebot_util.broker_base import Position
from tradebot_util.live_executor_v5 import build_order_intents


def test_build_order_intents_buy_sell_and_ignore_cash():
    target = pd.Series({"AAA3": 0.40, "BBB3": 0.20, "CASH": 0.40})
    current = pd.Series({"AAA3": 0.10, "CCC3": 0.20, "CASH": 0.70})
    intents = build_order_intents(target, current, account_equity=10000, min_order_value=50)
    by_ticker = {intent.ticker: intent for intent in intents}
    assert by_ticker["AAA3"].side == "BUY"
    assert by_ticker["AAA3"].delta_value == 3000
    assert by_ticker["BBB3"].side == "BUY"
    assert by_ticker["CCC3"].side == "SELL"
    assert "CASH" not in by_ticker


def test_position_dataclass():
    position = Position("AAA3", 10, 1234.56)
    assert position.ticker == "AAA3"
    assert position.market_value == 1234.56
