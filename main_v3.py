from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tradebot_util.backtest_v3 import run_backtest_v3, save_backtest_v3
from tradebot_util.config import load_config
from tradebot_util.market_data import download_adjusted_close, download_volume
from tradebot_util.regime import detect_regime
from tradebot_util.scoring import final_scores
from tradebot_util.universe import load_universe, tickers


def load_prices(config, args, tickers_list):
    if args.prices_csv:
        prices = pd.read_csv(args.prices_csv, index_col=0, parse_dates=True)
        cols = [ticker for ticker in tickers_list if ticker in prices.columns]
        return prices[cols].dropna(how="all")
    start = config.get("data", {}).get("start", "2018-01-01")
    return download_adjusted_close(tickers_list, start=start, auto_adjust=True)


def print_metrics(metrics):
    for key, value in metrics.items():
        if "final_value" in key:
            print(f"{key}: R$ {value:,.2f}")
        elif any(word in key for word in ["return", "drawdown", "alpha", "volatility", "error", "ratio"]):
            print(f"{key}: {value:.2%}")
        else:
            print(f"{key}: {value:.4f}")


def cmd_show_config(args):
    config = load_config(args.config)
    assets = load_universe(config)
    print(f"Estratégia: {config.get('strategy', {}).get('name')}")
    print(f"Versão: {config.get('strategy', {}).get('version')}")
    print(f"Benchmark: {config.get('strategy', {}).get('benchmark')}")
    print(f"Ativos no universo: {len(assets)}")
    for asset in assets:
        print(f"{asset.ticker:7s} {asset.index_weight:7.2%} {asset.sector} - {asset.name}")


def cmd_rank(args):
    config = load_config(args.config)
    assets = load_universe(config)
    tickers_list = tickers(assets)
    prices = load_prices(config, args, tickers_list)
    volume = None
    if not args.prices_csv:
        try:
            volume = download_volume(list(prices.columns), start=config.get("data", {}).get("start", "2018-01-01"))
        except Exception:
            volume = None
    scores = final_scores(prices, config, volume=volume)
    regime = detect_regime(prices, config)
    print(f"Regime V3: {regime.regime} | Exposição base em ações: {regime.equity_exposure:.0%}")
    print(scores.round(2).to_string())


def cmd_backtest(args):
    config = load_config(args.config)
    assets = load_universe(config)
    tickers_list = tickers(assets)
    prices = load_prices(config, args, tickers_list)
    result = run_backtest_v3(
        prices=prices,
        assets=assets,
        config=config,
        benchmark_csv=args.benchmark_csv,
        strict_real_benchmark=args.strict_real_benchmark,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    output_dir = args.output_dir or config.get("backtest", {}).get("output_dir", "backtests/results_v3")
    out = save_backtest_v3(result, output_dir)
    print("Métricas do backtest V3")
    print(f"Benchmark primário usado: {result.primary_benchmark_name}")
    print_metrics(result.metrics)
    print("\nCarteira final V3")
    final_portfolio = result.final_portfolio.copy()
    final_portfolio["weight_pct"] = final_portfolio["weight_pct"].map(lambda x: f"{x:.2f}%")
    final_portfolio["score"] = final_portfolio["score"].map(lambda x: "" if pd.isna(x) else f"{x:.2f}")
    print(final_portfolio[["ticker", "name", "sector", "weight_pct", "score"]].to_string(index=False))
    print(f"\nArquivos V3 salvos em: {out}")


def build_parser():
    parser = argparse.ArgumentParser(description="Tradebot UTIL V3")
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_config = subparsers.add_parser("show-config")
    show_config.add_argument("--config", default="config_v3.yaml")
    show_config.set_defaults(func=cmd_show_config)

    rank = subparsers.add_parser("rank")
    rank.add_argument("--config", default="config_v3.yaml")
    rank.add_argument("--prices-csv", default=None)
    rank.set_defaults(func=cmd_rank)

    backtest = subparsers.add_parser("backtest")
    backtest.add_argument("--config", default="config_v3.yaml")
    backtest.add_argument("--prices-csv", default=None)
    backtest.add_argument("--benchmark-csv", default=None)
    backtest.add_argument("--strict-real-benchmark", action="store_true")
    backtest.add_argument("--start-date", default=None)
    backtest.add_argument("--end-date", default=None)
    backtest.add_argument("--output-dir", default=None)
    backtest.set_defaults(func=cmd_backtest)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
