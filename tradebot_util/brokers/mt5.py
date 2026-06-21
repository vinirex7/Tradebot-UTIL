from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import MetaTrader5 as mt5

from tradebot_util.broker_base import Position


@dataclass
class MT5Broker:
    symbol_map: Dict[str, str]
    deviation: int = 20
    magic: int = 5052026
    dry_run: bool = True
    max_order_value: float = 200.0

    def __post_init__(self):
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

        account = mt5.account_info()
        terminal = mt5.terminal_info()

        if account is None:
            raise RuntimeError(f"MT5 account_info failed: {mt5.last_error()}")

        if terminal is None:
            raise RuntimeError(f"MT5 terminal_info failed: {mt5.last_error()}")

        if not terminal.connected:
            raise RuntimeError("Terminal MT5 não está conectado ao servidor da corretora.")

        if not terminal.trade_allowed:
            raise RuntimeError("Negociação algorítmica não está liberada no terminal MT5.")

        if not account.trade_allowed:
            raise RuntimeError("Negociação não está liberada nesta conta MT5.")

    def _mt5_symbol(self, ticker: str) -> str:
        return self.symbol_map.get(ticker, ticker)

    def account_equity(self) -> float:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError(f"MT5 account_info failed: {mt5.last_error()}")
        return float(account.equity)

    def positions(self) -> list[Position]:
        raw_positions = mt5.positions_get()
        if raw_positions is None:
            raw_positions = []

        reverse_map = {v: k for k, v in self.symbol_map.items()}
        result: list[Position] = []

        for pos in raw_positions:
            ticker = reverse_map.get(pos.symbol, pos.symbol)
            info = mt5.symbol_info(pos.symbol)
            contract_size = float(info.trade_contract_size) if info else 1.0
            market_value = float(pos.price_current) * float(pos.volume) * contract_size

            result.append(
                Position(
                    ticker=ticker,
                    quantity=float(pos.volume),
                    market_value=market_value,
                )
            )

        return result

    def submit_order_value(self, ticker: str, side: str, value: float) -> str:
        value = abs(float(value))

        if value <= 0:
            return f"SKIPPED {ticker}: valor <= 0"

        if value > self.max_order_value:
            raise RuntimeError(
                f"Ordem bloqueada por segurança: valor R$ {value:.2f} acima do limite "
                f"R$ {self.max_order_value:.2f}. Ajuste max_order_value com cuidado."
            )

        symbol = self._mt5_symbol(ticker)

        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Não consegui selecionar símbolo no MT5: {symbol}")

        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)

        if info is None:
            raise RuntimeError(f"symbol_info retornou None para {symbol}")

        if tick is None:
            raise RuntimeError(f"symbol_info_tick retornou None para {symbol}")

        side = side.upper()
        if side not in {"BUY", "SELL"}:
            raise ValueError(f"side inválido: {side}")

        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        price = float(tick.ask if side == "BUY" else tick.bid)

        if price <= 0:
            raise RuntimeError(f"Preço inválido para {symbol}: {price}")

        contract_size = float(info.trade_contract_size) if info.trade_contract_size else 1.0
        volume_step = float(info.volume_step)
        min_volume = float(info.volume_min)

        raw_volume = value / (price * contract_size)
        volume = round(raw_volume / volume_step) * volume_step
        volume = max(min_volume, volume)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": "Tradebot-UTIL V5",
            "type_time": mt5.ORDER_TIME_DAY,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        check = mt5.order_check(request)
        if check is None:
            raise RuntimeError(f"order_check retornou None para {symbol}: {mt5.last_error()}")

        if check.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"order_check recusou {side} {symbol}: {check}")

        if self.dry_run:
            return f"MT5_DRY_RUN_OK {side} {symbol} volume={volume} value={value:.2f}"

        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"order_send retornou None para {symbol}: {mt5.last_error()}")

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"order_send falhou para {side} {symbol}: {result}")

        return f"MT5_ORDER_SENT {side} {symbol} volume={volume} order={result.order}"
