from __future__ import annotations

import pandas as pd


def format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def metrics_to_frame(metrics: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame({"metric": list(metrics.keys()), "value": list(metrics.values())})
