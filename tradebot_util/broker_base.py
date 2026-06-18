from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Position:
    ticker: str
    quantity: float
    market_value: float


@dataclass(frozen=True)
class OrderIntent:
    ticker: str
    side: str
    target_weight: float
    current_weight: float
    target_value: float
    current_value: float
    delta_value: float


class BrokerAdapter(Protocol):
    def account_equity(self) -> float:
        ...

    def positions(self) -> list[Position]:
        ...

    def submit_order_value(self, ticker: str, side: str, value: float) -> str:
        ...


class BrokerNotImplementedError(RuntimeError):
    pass
