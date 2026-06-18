from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .universe import Asset, load_universe

TICKER_COLUMNS = ["ticker", "Ticker", "Código", "Codigo", "codigo", "Código de Negociação", "Código de Negociacao", "Ativo", "ativo"]
NAME_COLUMNS = ["name", "Name", "Nome", "Empresa", "Nome da Empresa", "Especificação", "Especificacao"]
SECTOR_COLUMNS = ["sector", "Sector", "Setor", "setor", "Segmento", "segmento"]
WEIGHT_COLUMNS = ["index_weight", "weight", "Weight", "Peso", "peso", "Part. (%)", "Part (%)", "Participação", "Participacao", "Part"]


@dataclass(frozen=True)
class UniverseUpdateResult:
    assets: list[Asset]
    active_path: Path
    report_path: Path
    added: list[str]
    removed: list[str]
    kept: list[str]
    source: str


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    normalized = {str(col).strip().lower(): col for col in df.columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in normalized:
            return str(normalized[key])
    return None


def _parse_weight(value: Any) -> float:
    if pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace("%", "")
        text = text.replace(".", "").replace(",", ".")
        number = float(text) if text else 0.0
    if number > 1.0:
        number = number / 100.0
    return max(0.0, number)


def _clean_ticker(value: Any) -> str:
    ticker = str(value).strip().upper()
    ticker = ticker.replace(".SA", "")
    ticker = ticker.replace(" ", "")
    return ticker


def _read_csv_flexible(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Universe CSV not found: {csv_path}")

    attempts = [
        {"sep": ",", "encoding": "utf-8"},
        {"sep": ";", "encoding": "utf-8"},
        {"sep": "\t", "encoding": "utf-8"},
        {"sep": ",", "encoding": "latin1"},
        {"sep": ";", "encoding": "latin1"},
        {"sep": "\t", "encoding": "latin1"},
    ]
    last_error: Exception | None = None
    for kwargs in attempts:
        try:
            df = pd.read_csv(csv_path, **kwargs)
            if len(df.columns) >= 2:
                return df
        except Exception as exc:  # pragma: no cover - defensive fallback
            last_error = exc
    if last_error:
        raise last_error
    raise ValueError(f"Could not parse universe CSV: {csv_path}")


def parse_universe_csv(path: str | Path) -> list[Asset]:
    df = _read_csv_flexible(path)
    df.columns = [str(col).strip() for col in df.columns]

    ticker_col = _find_column(df, TICKER_COLUMNS)
    if ticker_col is None:
        raise ValueError(f"Universe CSV must include a ticker column. Columns found: {list(df.columns)}")

    name_col = _find_column(df, NAME_COLUMNS)
    sector_col = _find_column(df, SECTOR_COLUMNS)
    weight_col = _find_column(df, WEIGHT_COLUMNS)

    rows: list[Asset] = []
    for _, item in df.iterrows():
        ticker = _clean_ticker(item[ticker_col])
        if not ticker or ticker in {"NAN", "CÓDIGO", "CODIGO", "TICKER"}:
            continue
        name = str(item[name_col]).strip() if name_col and not pd.isna(item[name_col]) else ticker
        sector = str(item[sector_col]).strip() if sector_col and not pd.isna(item[sector_col]) else "Unknown"
        weight = _parse_weight(item[weight_col]) if weight_col else 0.0
        rows.append(Asset(ticker=ticker, name=name, sector=sector, index_weight=weight))

    if not rows:
        raise ValueError(f"No valid assets found in universe CSV: {path}")

    total = sum(asset.index_weight for asset in rows)
    if total <= 0:
        equal = 1.0 / len(rows)
        return [Asset(a.ticker, a.name, a.sector, equal) for a in rows]

    return [Asset(a.ticker, a.name, a.sector, a.index_weight / total) for a in rows]


def assets_to_frame(assets: list[Asset]) -> pd.DataFrame:
    return pd.DataFrame([
        {"ticker": asset.ticker, "name": asset.name, "sector": asset.sector, "index_weight": asset.index_weight}
        for asset in assets
    ])


def save_assets_csv(assets: list[Asset], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    assets_to_frame(assets).to_csv(output, index=False)
    return output


def _diff_assets(previous: list[Asset], current: list[Asset]) -> tuple[list[str], list[str], list[str]]:
    previous_tickers = {asset.ticker for asset in previous}
    current_tickers = {asset.ticker for asset in current}
    added = sorted(current_tickers - previous_tickers)
    removed = sorted(previous_tickers - current_tickers)
    kept = sorted(current_tickers & previous_tickers)
    return added, removed, kept


def update_dynamic_universe(config: dict[str, Any], source_csv: str | None = None) -> UniverseUpdateResult:
    universe_cfg = config.get("universe", {})
    latest_path = Path(source_csv or universe_cfg.get("latest_snapshot_path", "data/universe/UTIL_carteira_atual.csv"))
    previous_path = Path(universe_cfg.get("previous_snapshot_path", "data/universe/UTIL_carteira_anterior.csv"))
    active_path = Path(universe_cfg.get("active_universe_path", "data/universe/UTIL_universe_active.csv"))
    report_path = Path(universe_cfg.get("update_report_path", "data/universe/UTIL_universe_update_report.csv"))

    current_assets = parse_universe_csv(latest_path)

    if active_path.exists():
        previous_assets = parse_universe_csv(active_path)
    elif previous_path.exists():
        previous_assets = parse_universe_csv(previous_path)
    else:
        previous_assets = load_universe(config)

    added, removed, kept = _diff_assets(previous_assets, current_assets)
    save_assets_csv(current_assets, active_path)

    report = pd.DataFrame([
        {"ticker": ticker, "status": "ADDED"} for ticker in added
    ] + [
        {"ticker": ticker, "status": "REMOVED"} for ticker in removed
    ] + [
        {"ticker": ticker, "status": "KEPT"} for ticker in kept
    ])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(report_path, index=False)

    return UniverseUpdateResult(
        assets=current_assets,
        active_path=active_path,
        report_path=report_path,
        added=added,
        removed=removed,
        kept=kept,
        source=str(latest_path),
    )


def load_active_universe_or_config(config: dict[str, Any]) -> list[Asset]:
    universe_cfg = config.get("universe", {})
    active_path = Path(universe_cfg.get("active_universe_path", "data/universe/UTIL_universe_active.csv"))
    latest_path = Path(universe_cfg.get("latest_snapshot_path", "data/universe/UTIL_carteira_atual.csv"))
    allow_fallback = bool(universe_cfg.get("allow_config_fallback", True))

    if active_path.exists():
        return parse_universe_csv(active_path)
    if latest_path.exists():
        result = update_dynamic_universe(config, source_csv=str(latest_path))
        return result.assets
    if allow_fallback:
        return load_universe(config)
    raise FileNotFoundError(f"Dynamic universe enabled but no active/latest universe CSV found: {active_path} / {latest_path}")
