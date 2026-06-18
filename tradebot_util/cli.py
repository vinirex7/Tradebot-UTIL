from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .backtest import run_backtest
from .config import load_config
from .market_data import download_adjusted_close, download_volume
from .regime import detect_regime
from .scoring import final_scores
from .universe import load_universe, tickers


def _load_prices(config: dict, args: argparse.Namespace, tickers_list: list[str]) -> pd.DataFrame:
    if getattr(args, "prices_csv", None):
        prices = pd.read_csv(args.prices_csv, index_col=0, parse_dates=True)
        return prices[tickers_list].dropna(how="all")

    start = config.get("data", {}).get("start", "2018-01-01")
    return download_adjusted_close(tickers_list, start=start, auto_adjust=True)


def cmd_rank(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    assets = load_universe(config)
    tickers_list = tickers(assets)
    prices = _load_prices(config, args, tickers_list)

    volume = None
    if not getattr(args, "prices_csv", None):
        try:
            volume = download_volume(tickers_list, start=config.get("data", {}).get("start", "2018-01-01"))
        except Exception:
            volume = None

    scores = final_scores(prices, config, volume=volume)
    regime = detect_regime(prices, config)

    print(f"Regime: {regime.regime} | Exposição alvo em ações: {regime.equity_exposure:.0%}")
    print(scores.round(2).to_string())


def cmd_backtest(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    assets = load_universe(config)
    tickers_list = tickers(assets)
    prices = _load_prices(config, args, tickers_list)
    result = run_backtest(prices, assets, config)

    print("Métricas do backtest")
    for key, value in result.metrics.items():
        if "return" in key or "drawdown" in key or "alpha" in key or "volatility" in key or "error" in key:
            print(f"{key}: {value:.2%}")
        else:
            print(f"{key}: {value:.3f}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result.equity_curve.to_csv(output_dir / "equity_curve.csv", header=["equity"])
    result.benchmark_curve.to_csv(output_dir / "benchmark_curve.csv", header=["benchmark"])
    result.weights_history.to_csv(output_dir / "weights_history.csv")
    print(f"Arquivos salvos em: {output_dir}")


def cmd_show_config(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    assets = load_universe(config)
    print(f"Estratégia: {config.get('strategy', {}).get('name')}")
    print(f"Ativos no universo: {len(assets)}")
    for asset in assets:
        print(f"{asset.ticker:7s} {asset.index_weight:7.2%} {asset.sector} - {asset.name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tradebot UTIL")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rank = subparsers.add_parser("rank", help="Calcula ranking e scores atuais")
    rank.add_argument("--config", default="config.yaml")
    rank.add_argument("--prices-csv", default=None, help="CSV opcional com preços ajustados")
    rank.set_defaults(func=cmd_rank)

    backtest = subparsers.add_parser("backtest", help="Roda backtest mensal")
    backtest.add_argument("--config", default="config.yaml")
    backtest.add_argument("--prices-csv", default=None, help="CSV opcional com preços ajustados")
    backtest.add_argument("--output-dir", default="backtests/results")
    backtest.set_defaults(func=cmd_backtest)

    show_config = subparsers.add_parser("show-config", help="Mostra universo e parâmetros principais")
    show_config.add_argument("--config", default="config.yaml")
    show_config.set_defaults(func=cmd_show_config)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
