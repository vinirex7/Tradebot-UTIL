from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Asset:
    ticker: str
    name: str
    sector: str
    index_weight: float

    @property
    def yf_ticker(self) -> str:
        return f"{self.ticker}.SA"


def load_universe(config: dict[str, Any]) -> list[Asset]:
    assets_cfg = config.get("universe", {}).get("assets", {})
    assets: list[Asset] = []

    for ticker, item in assets_cfg.items():
        assets.append(
            Asset(
                ticker=ticker,
                name=str(item.get("name", ticker)),
                sector=str(item.get("sector", "Unknown")),
                index_weight=float(item.get("index_weight", 0.0)),
            )
        )

    if not assets:
        raise ValueError("No assets found in config universe.assets")

    total = sum(asset.index_weight for asset in assets)
    if total <= 0:
        equal = 1.0 / len(assets)
        return [Asset(a.ticker, a.name, a.sector, equal) for a in assets]

    return [Asset(a.ticker, a.name, a.sector, a.index_weight / total) for a in assets]


def tickers(assets: list[Asset]) -> list[str]:
    return [asset.ticker for asset in assets]
