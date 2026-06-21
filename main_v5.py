from __future__ import annotations

import argparse

import pandas as pd

from tradebot_util.backtest_v4 import run_backtest_v4, save_backtest_v4
from tradebot_util.config import load_config
from tradebot_util.live_executor_v5 import run_live_cycle_v5
from tradebot_util.market_data import download_adjusted_close, download_volume
from tradebot_util.strategy_live_v5 import generate_live_decision_v5, save_live_decision
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
    decision = generate_live_decision_v5(
        config_path=args.config,
        benchmark_csv=args.benchmark_csv,
        universe_csv=args.universe_csv,
        prices_csv=args.prices_csv,
        update_universe_first=args.update_universe_first,
    )
    print(f"Regime V5: {decision.regime} | Exposição base em ações: {decision.equity_exposure:.0%}")
    print(f"Benchmark usado no regime: {decision.benchmark_used}")
    print(f"Universo ativo: {decision.universe_size} ativos")
    print(decision.scores.round(2).to_string())


def cmd_decide(args):
    decision = generate_live_decision_v5(
        config_path=args.config,
        benchmark_csv=args.benchmark_csv,
        universe_csv=args.universe_csv,
        prices_csv=args.prices_csv,
        update_universe_first=args.update_universe_first,
    )
    out = save_live_decision(decision, output_dir=args.output_dir)
    target = decision.target_weights.copy()
    target.loc["CASH"] = max(0.0, 1.0 - float(target.sum()))
    print("Decisão live V5 gerada")
    print(f"Data base: {decision.as_of}")
    print(f"Regime: {decision.regime}")
    print(f"Benchmark usado: {decision.benchmark_used}")
    print(f"Universo ativo: {decision.universe_size} ativos")
    print("\nPesos alvo")
    for ticker, weight in target.sort_values(ascending=False).items():
        print(f"{ticker:7s} {weight:7.2%}")
    print(f"\nArquivos salvos em: {out}")


def cmd_live_cycle(args):
    result = run_live_cycle_v5(
        mode=args.mode,
        config_path=args.config,
        benchmark_csv=args.benchmark_csv,
        universe_csv=args.universe_csv,
        prices_csv=args.prices_csv,
        update_universe_first=args.update_universe_first,
        output_dir=args.output_dir,
        min_order_value=args.min_order_value,
        apply_paper_targets=args.apply_paper_targets,
        confirm_live=args.confirm_live,
        max_live_order_value=args.max_live_order_value,
    )
    print("Ciclo live V5 concluído")
    print(f"Modo: {result.mode}")
    print(f"Data base: {result.as_of}")
    print(f"Regime: {result.regime}")
    print(f"Benchmark usado: {result.benchmark_used}")
    print(f"Universo ativo: {result.universe_size} ativos")
    print(f"Patrimônio base: R$ {result.account_equity:,.2f}")
    print(f"Ordens/intents geradas: {len(result.intents)}")
    for intent in result.intents:
        print(f"{intent.side:4s} {intent.ticker:7s} delta R$ {intent.delta_value:,.2f} alvo {intent.target_weight:.2%}")
    print(f"Arquivos salvos em: {result.output_dir}")


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


def add_common_strategy_args(parser):
    parser.add_argument("--config", default="config_v5.yaml")
    parser.add_argument("--prices-csv", default=None)
    parser.add_argument("--benchmark-csv", default=None)
    parser.add_argument("--universe-csv", default=None)
    parser.add_argument("--update-universe-first", action="store_true")


def build_parser():
    parser = argparse.ArgumentParser(description="Tradebot UTIL V5 - Dynamic Universe + Live/Paper")
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
    add_common_strategy_args(rank)
    rank.set_defaults(func=cmd_rank)

    decide = subparsers.add_parser("decide", help="Gera decisão live sem enviar ordens")
    add_common_strategy_args(decide)
    decide.add_argument("--output-dir", default="state/live")
    decide.set_defaults(func=cmd_decide)

    live_cycle = subparsers.add_parser("live-cycle", help="Gera decisão e intenções de ordem em dry-run/paper")
    add_common_strategy_args(live_cycle)
    live_cycle.add_argument("--mode", choices=["dry-run", "paper", "mt5-dry-run", "mt5-live"], default="paper")
    live_cycle.add_argument("--output-dir", default="state/live")
    live_cycle.add_argument("--min-order-value", type=float, default=50.0)
    live_cycle.add_argument("--max-live-order-value", type=float, default=200.0)
    live_cycle.add_argument("--apply-paper-targets", action="store_true")
    live_cycle.add_argument("--confirm-live", action="store_true")
    live_cycle.set_defaults(func=cmd_live_cycle)

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
