from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .broker_base import BrokerAdapter, OrderIntent, Position
from .brokers.paper import PaperBroker
from .strategy_live_v5 import LiveDecisionV5, generate_live_decision_v5, save_live_decision


@dataclass(frozen=True)
class LiveRunResult:
    mode: str
    as_of: str
    regime: str
    benchmark_used: str
    universe_size: int
    account_equity: float
    intents: list[OrderIntent]
    output_dir: Path


def _positions_to_weights(positions: list[Position], equity: float) -> pd.Series:
    if equity <= 0:
        raise ValueError("Patrimônio da conta precisa ser maior que zero")
    data = {position.ticker: position.market_value / equity for position in positions}
    return pd.Series(data, dtype=float)


def build_order_intents(target_weights: pd.Series, current_weights: pd.Series, account_equity: float, min_order_value: float = 50.0) -> list[OrderIntent]:
    target = target_weights.copy().clip(lower=0.0)
    target.loc["CASH"] = max(0.0, 1.0 - float(target.drop(labels=["CASH"], errors="ignore").sum()))
    current = current_weights.copy().clip(lower=0.0)
    all_tickers = sorted(set(target.index) | set(current.index))
    intents: list[OrderIntent] = []

    for ticker in all_tickers:
        if ticker == "CASH":
            continue
        target_weight = float(target.get(ticker, 0.0))
        current_weight = float(current.get(ticker, 0.0))
        target_value = target_weight * account_equity
        current_value = current_weight * account_equity
        delta_value = target_value - current_value
        if abs(delta_value) < min_order_value:
            continue
        side = "BUY" if delta_value > 0 else "SELL"
        intents.append(OrderIntent(
            ticker=ticker,
            side=side,
            target_weight=target_weight,
            current_weight=current_weight,
            target_value=target_value,
            current_value=current_value,
            delta_value=delta_value,
        ))
    return intents


def _save_intents(intents: list[OrderIntent], output_dir: Path) -> Path:
    rows = [intent.__dict__ for intent in intents]
    path = output_dir / "order_intents.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def run_live_cycle_v5(
    mode: str = "paper",
    config_path: str = "config_v5.yaml",
    benchmark_csv: str | None = None,
    universe_csv: str | None = None,
    prices_csv: str | None = None,
    update_universe_first: bool = False,
    output_dir: str | Path = "state/live",
    min_order_value: float = 50.0,
    apply_paper_targets: bool = False,
) -> LiveRunResult:
    decision: LiveDecisionV5 = generate_live_decision_v5(
        config_path=config_path,
        benchmark_csv=benchmark_csv,
        universe_csv=universe_csv,
        prices_csv=prices_csv,
        update_universe_first=update_universe_first,
    )
    out = save_live_decision(decision, output_dir=output_dir)

    if mode not in {"dry-run", "paper"}:
        raise RuntimeError("Execução real bloqueada. Modos permitidos agora: dry-run ou paper.")

    broker: BrokerAdapter = PaperBroker() if mode == "paper" else PaperBroker(state_path=Path(out) / "dry_run_positions.csv")
    account_equity = broker.account_equity()
    current_weights = _positions_to_weights(broker.positions(), account_equity)
    intents = build_order_intents(decision.target_weights, current_weights, account_equity, min_order_value=min_order_value)
    _save_intents(intents, out)

    if mode == "paper" and apply_paper_targets:
        paper = broker if isinstance(broker, PaperBroker) else None
        if paper is not None:
            target = decision.target_weights.copy()
            target.loc["CASH"] = max(0.0, 1.0 - float(target.sum()))
            paper.set_target_weights(target)

    return LiveRunResult(
        mode=mode,
        as_of=decision.as_of,
        regime=decision.regime,
        benchmark_used=decision.benchmark_used,
        universe_size=decision.universe_size,
        account_equity=account_equity,
        intents=intents,
        output_dir=out,
    )
