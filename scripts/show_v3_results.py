from __future__ import annotations

from pathlib import Path

import pandas as pd


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    out = Path("backtests/results_v3")
    metrics_path = out / "metrics_v3.csv"
    portfolio_path = out / "final_portfolio_v3.csv"
    comparison_path = out / "comparison_curves_v3.csv"

    if not metrics_path.exists():
        raise FileNotFoundError("Rode primeiro: python main_v3.py backtest --config config_v3.yaml")

    metrics = pd.read_csv(metrics_path).set_index("metric")["value"]
    print("Resumo V3")
    print(f"Bot final:              R$ {metrics['bot_final_value']:,.2f}")
    print(f"Benchmark primário:     R$ {metrics['primary_benchmark_final_value']:,.2f}")
    print(f"Proxy ponderado:        R$ {metrics['weighted_proxy_final_value']:,.2f}")
    print(f"Equal-weight:           R$ {metrics['equal_weight_final_value']:,.2f}")
    print(f"Retorno bot:            {pct(metrics['bot_total_return'])}")
    print(f"Retorno benchmark:      {pct(metrics['primary_benchmark_total_return'])}")
    print(f"Alpha vs benchmark:     {pct(metrics['alpha_vs_primary'])}")
    print(f"Sharpe bot:             {metrics['bot_sharpe']:.3f}")
    print(f"Drawdown bot:           {pct(metrics['bot_max_drawdown'])}")
    print(f"Drawdown benchmark:     {pct(metrics['primary_benchmark_max_drawdown'])}")
    print(f"Info ratio vs benchmark:{metrics['information_ratio_vs_primary']:.3f}")

    if portfolio_path.exists():
        print("\nCarteira final")
        portfolio = pd.read_csv(portfolio_path)
        portfolio["weight_pct"] = portfolio["weight_pct"].map(lambda x: f"{x:.2f}%")
        print(portfolio[["ticker", "name", "sector", "weight_pct", "score"]].to_string(index=False))

    if comparison_path.exists():
        print(f"\nCurvas comparativas salvas em: {comparison_path}")


if __name__ == "__main__":
    main()
