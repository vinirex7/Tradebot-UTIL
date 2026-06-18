from __future__ import annotations

import argparse

import pandas as pd

from tradebot_util.backtest_v4 import run_backtest_v4, save_backtest_v4
from tradebot_util.config import load_config
from tradebot_util.market_data import download_adjusted_close, download_volume
from tradebot_util.regime import detect_regime
from tradebot_util.scoring import final_scores
from tradebot_util.universe import tickers
from tradebot_util.universe_dynamic_v5 import load_active_universe_or_config, update_dynamic_universe


def load_prices(config, args, tickers_list):
    if args.prices_csv:
        prices = pd.read_csv(args.prices_csv, index_col=0, parse_dates=True)
        cols = [ticker for ticker in tickers_list if ticker in prices.columns]
        return prices[cols].dropna(how="all")
    start = config.get("data", {}).get("start", "2018-01-01")
    return download_adjusted_close(tickers_list, start=start, auto_adjust=True)


def print_metrics(metrics):
    percent_words = ["return", "drawdown", "alpha", "volatility", "error"]
    for key, value in metrics.items():
        if "final_value" in key:
            print(f"{key}: R$ {value:,.2f}")
        elif any(word in key for word in percent_words):
            print(f"{key}: {value:.2%}")
        else:
            print(f"{key}: {value:.4f}")


def cmd_update_universe(args):
    config = load_config(args.config)
    result = update_dynamic_universe(config, source_csv=args.universe_csv)
    print("Universo UTIL atualizado")
    print(f"Fonte: {result.source}")
    print(f"Arquivo ativo: {result.active_path}")
    print(f"Relatório: {result.report_path}")
    print(f"Ativos atuais: {len(result.assets)}")
    print(f"Adicionados: {', '.join(result.added) if result.added else 'nenhum'}")
    print(f"Removidos: {', '.join(result.removed) if result.removed else 'nenhum'}")


def cmd_show_universe(args):
    config = load_config(args.config)
    assets = load_active_universe_or_config(config)
    print(f"Ativos no universo ativo: {len(assets)}")
    for asset in assets:
        print(f"{asset.ticker:7s} {asset.index_weight:7.2%} {asset.sector} - {asset.name}")


def cmd_show_config(args):
    config = load_config(args.config)
    assets = load_active_universe_or_config(config)
    print(f"Estratégia: {config.get('strategy', {}).get('name')}")
    print(f"Versão: {config.get('strategy', {}).get('version')}")
    print(f"Benchmark: {config.get('strategy', {}).get('benchmark')}")
    print(f"Dynamic universe: {config.get('universe', {}).get('dynamic_universe')}")
    print(f"Ativos no universo ativo: {len(assets)}")


def cmd_rank(args):
    config = load_config(args.config)
    if args.update_universe_first:
        update_dynamic_universe(config, source_csv=args.universe_csv)
    assets = load_active_universe_or_config(config)
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
    print(f"Regime V5: {regime.regime} | Exposição base em ações: {regime.equity_exposure:.0%}")
    print(scores.round(2).to_string())


def cmd_backtest(args):
    config = load_config(args.config)
    if args.update_universe_first:
        update_dynamic_universe(config, source_csv=args.universe_csv)
    assets = load_active_universe_or_config(config)
    tickers_list = tickers(assets)
    prices = load_prices(config, args, tickers_list)
    result = run_backtest_v4(
        prices=prices,
        assets=assets,
        config=config,
        benchmark_csv=args.benchmark_csv,
        strict_real_benchmark=args.strict_real_benchmark,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    output_dir = args.output_dir or config.get("backtest", {}).get("output_dir", "backtests/results_v5")
    out = save_backtest_v4(result, output_dir)
    print("Métricas do backtest V5")
    print(f"Benchmark primário usado: {result.primary_benchmark_name}")
    print(f"Universo ativo usado: {len(assets)} ativos")
    print_metrics(result.metrics)
    print("\nCarteira final V5")
    final_portfolio = result.final_portfolio.copy()
    final_portfolio["weight_pct"] = final_portfolio["weight_pct"].map(lambda x: f"{x:.2f}%")
    final_portfolio["score"] = final_portfolio["score"].map(lambda x: "" if pd.isna(x) else f"{x:.2f}")
    print(final_portfolio[["ticker", "name", "sector", "weight_pct", "score"]].to_string(index=False))
    print(f"\nArquivos V5 salvos em: {out}")


def build_parser():
    parser = argparse.ArgumentParser(description="Tradebot UTIL V5 - Dynamic Universe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    update_universe = subparsers.add_parser("update-universe", help="Atualiza o universo ativo do UTIL a partir de CSV")
    update_universe.add_argument("--config", default="config_v5.yaml")
    update_universe.add_argument("--universe-csv", default=None, help="CSV com a carteira atual do UTIL")
    update_universe.set_defaults(func=cmd_update_universe)

    show_universe = subparsers.add_parser("show-universe", help="Mostra o universo ativo usado pelo bot")
    show_universe.add_argument("--config", default="config_v5.yaml")
    show_universe.set_defaults(func=cmd_show_universe)

    show_config = subparsers.add_parser("show-config")
    show_config.add_argument("--config", default="config_v5.yaml")
    show_config.set_defaults(func=cmd_show_config)

    rank = subparsers.add_parser("rank")
    rank.add_argument("--config", default="config_v5.yaml")
    rank.add_argument("--prices-csv", default=None)
    rank.add_argument("--universe-csv", default=None)
    rank.add_argument("--update-universe-first", action="store_true")
    rank.set_defaults(func=cmd_rank)

    backtest = subparsers.add_parser("backtest")
    backtest.add_argument("--config", default="config_v5.yaml")
    backtest.add_argument("--prices-csv", default=None)
    backtest.add_argument("--benchmark-csv", default=None)
    backtest.add_argument("--universe-csv", default=None)
    backtest.add_argument("--update-universe-first", action="store_true")
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
