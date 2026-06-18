from __future__ import annotations

from tradebot_util.broker_base import BrokerNotImplementedError, Position


class NullBroker:
    def account_equity(self) -> float:
        raise BrokerNotImplementedError("Nenhuma corretora real foi configurada. Use paper trading ou implemente um adapter real.")

    def positions(self) -> list[Position]:
        raise BrokerNotImplementedError("Nenhuma corretora real foi configurada. Use paper trading ou implemente um adapter real.")

    def submit_order_value(self, ticker: str, side: str, value: float) -> str:
        raise BrokerNotImplementedError("Ordem real bloqueada: nenhuma corretora real foi configurada.")
