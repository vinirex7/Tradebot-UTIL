from __future__ import annotations

from pathlib import Path

import pandas as pd


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    out = Path("backtests/results_v2")
    metrics_path = out / "metrics_v2.csv"
    portfolio_path = out / "final_portfolio_v2.csv"
    comparison_path = out / "comparison_curves_v2.csv"

    if not metrics_path.exists():
        raise FileNotFoundError("Rode primeiro: python main_v2.py backtest --config config_v2.yaml")

    metrics = pd.read_csv(metrics_path).set_index("metric")["value"]
    print("Resumo V2")
    print(f"Bot final:                    R$ {metrics['bot_final_value']:,.2f}")
    print(f"Benchmark ponderado final:    R$ {metrics['weighted_benchmark_final_value']:,.2f}")
    print(f"Benchmark equal-weight final: R$ {metrics['equal_weight_benchmark_final_value']:,.2f}")
    print(f"Retorno bot:                  {pct(metrics['bot_total_return'])}")
    print(f"Retorno bench ponderado:      {pct(metrics['weighted_benchmark_total_return'])}")
    print(f"Alpha vs ponderado:           {pct(metrics['alpha_vs_weighted_benchmark'])}")
    print(f"Drawdown bot:                 {pct(metrics['bot_max_drawdown'])}")
    print(f"Info ratio vs ponderado:      {metrics['information_ratio_vs_weighted']:.3f}")

    if portfolio_path.exists():
        print("\nCarteira final")
        portfolio = pd.read_csv(portfolio_path)
        portfolio["weight_pct"] = portfolio["weight_pct"].map(lambda x: f"{x:.2f}%")
        print(portfolio[["ticker", "name", "sector", "weight_pct", "score"]].to_string(index=False))

    if comparison_path.exists():
        print(f"\nCurvas comparativas salvas em: {comparison_path}")


if __name__ == "__main__":
    main()
