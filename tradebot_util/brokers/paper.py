from __future__ import annotations

from pathlib import Path

import pandas as pd

from tradebot_util.broker_base import Position


class PaperBroker:
    def __init__(self, state_path: str | Path = "state/paper/positions.csv", initial_equity: float = 10000.0):
        self.state_path = Path(state_path)
        self.initial_equity = float(initial_equity)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            pd.DataFrame([{"ticker": "CASH", "quantity": 1.0, "market_value": self.initial_equity}]).to_csv(self.state_path, index=False)

    def _read(self) -> pd.DataFrame:
        df = pd.read_csv(self.state_path)
        if df.empty:
            return pd.DataFrame([{"ticker": "CASH", "quantity": 1.0, "market_value": self.initial_equity}])
        return df

    def _write(self, df: pd.DataFrame) -> None:
        df.to_csv(self.state_path, index=False)

    def account_equity(self) -> float:
        return float(self._read()["market_value"].sum())

    def positions(self) -> list[Position]:
        df = self._read()
        return [Position(str(row.ticker), float(row.quantity), float(row.market_value)) for row in df.itertuples(index=False)]

    def set_target_weights(self, weights: pd.Series) -> None:
        equity = self.account_equity()
        weights = weights.copy().clip(lower=0.0)
        weights.loc["CASH"] = max(0.0, 1.0 - float(weights.drop(labels=["CASH"], errors="ignore").sum()))
        rows = []
        for ticker, weight in weights.items():
            value = float(weight) * equity
            if value <= 1e-9:
                continue
            rows.append({"ticker": ticker, "quantity": 1.0, "market_value": value})
        self._write(pd.DataFrame(rows))

    def submit_order_value(self, ticker: str, side: str, value: float) -> str:
        # Paper broker does not simulate intraday fills. The live executor applies the target portfolio directly.
        return f"PAPER-{side.upper()}-{ticker}-{abs(value):.2f}"
