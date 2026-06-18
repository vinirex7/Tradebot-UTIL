from __future__ import annotations

from pathlib import Path

import pandas as pd


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    out = Path("backtests/results_v4")
    metrics_path = out / "metrics_v4.csv"
    portfolio_path = out / "final_portfolio_v4.csv"
    weights_path = out / "weights_history_v4.csv"
    comparison_path = out / "comparison_curves_v4.csv"

    if not metrics_path.exists():
        raise FileNotFoundError("Rode primeiro: python3 main_v4.py backtest --config config_v4.yaml")

    metrics = pd.read_csv(metrics_path).set_index("metric")["value"]
    print("Resumo V4")
    print(f"Bot final:               R$ {metrics['bot_final_value']:,.2f}")
    print(f"Benchmark primário:      R$ {metrics['primary_benchmark_final_value']:,.2f}")
    print(f"Proxy ponderado:         R$ {metrics['weighted_proxy_final_value']:,.2f}")
    print(f"Equal-weight:            R$ {metrics['equal_weight_final_value']:,.2f}")
    print(f"Retorno bot:             {pct(metrics['bot_total_return'])}")
    print(f"Retorno benchmark:       {pct(metrics['primary_benchmark_total_return'])}")
    print(f"Alpha vs benchmark:      {pct(metrics['alpha_vs_primary'])}")
    print(f"Sharpe bot:              {metrics['bot_sharpe']:.3f}")
    print(f"Drawdown bot:            {pct(metrics['bot_max_drawdown'])}")
    print(f"Drawdown benchmark:      {pct(metrics['primary_benchmark_max_drawdown'])}")
    print(f"Info ratio vs benchmark: {metrics['information_ratio_vs_primary']:.3f}")

    if portfolio_path.exists():
        print("\nCarteira final")
        portfolio = pd.read_csv(portfolio_path)
        portfolio["weight_pct"] = portfolio["weight_pct"].map(lambda x: f"{x:.2f}%")
        print(portfolio[["ticker", "name", "sector", "weight_pct", "score"]].to_string(index=False))

    if weights_path.exists():
        weights = pd.read_csv(weights_path)
        if "ACTION" in weights.columns:
            print("\nAções de rebalanceamento")
            print(weights["ACTION"].value_counts().to_string())

    if comparison_path.exists():
        print(f"\nCurvas comparativas salvas em: {comparison_path}")


if __name__ == "__main__":
    main()
