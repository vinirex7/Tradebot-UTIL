from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TICKERS = ["AXIA3", "SBSP3", "EQTL3", "ENEV3", "CPLE3", "CMIG4", "ENGI11", "EGIE3", "ISAE4", "CSMG3", "TAEE11", "CPFE3", "SAPR11", "ALUP11", "ORVR3", "AURE3"]


def main() -> None:
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2020-01-01", periods=900)
    prices = pd.DataFrame(index=dates)
    for i, ticker in enumerate(TICKERS):
        drift = 0.00015 + i * 0.000005
        vol = 0.012 + (i % 4) * 0.002
        rets = rng.normal(drift, vol, size=len(dates))
        prices[ticker] = 20 * (1 + pd.Series(rets, index=dates)).cumprod()

    out = Path("data/processed/synthetic_prices.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(out)
    print(out)


if __name__ == "__main__":
    main()
