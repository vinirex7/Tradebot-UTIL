from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


def parse_br_number(value: str) -> float:
    cleaned = value.strip().replace(".", "").replace(",", ".")
    return float(cleaned)


def convert_investing_raw(raw_text: str) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    seen_dates: set[str] = set()

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        match = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})\s+([0-9\.]+,[0-9]{2})", line)
        if not match:
            continue

        day, month, year, close_raw = match.groups()
        iso_date = f"{year}-{month}-{day}"
        if iso_date in seen_dates:
            continue

        close = parse_br_number(close_raw)
        rows.append((iso_date, close))
        seen_dates.add(iso_date)

    rows.sort(key=lambda item: item[0])
    return rows


def write_csv(rows: list[tuple[str, float]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["date", "close"])
        for date, close in rows:
            writer.writerow([date, f"{close:.2f}"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Converte dados históricos do Investing do UTIL para date,close")
    parser.add_argument("--input", required=True, help="Arquivo .txt bruto copiado do Investing")
    parser.add_argument("--output", default="data/benchmarks/UTIL_historico.csv", help="CSV final para o bot")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    raw_text = input_path.read_text(encoding="utf-8")
    rows = convert_investing_raw(raw_text)

    if not rows:
        raise SystemExit("Nenhuma linha válida encontrada. Confira se o texto contém linhas tipo: 17.06.2026 17.788,62 ...")

    write_csv(rows, output_path)

    first_date, first_close = rows[0]
    last_date, last_close = rows[-1]
    total_return = last_close / first_close - 1.0

    print(f"Arquivo gerado: {output_path}")
    print(f"Linhas convertidas: {len(rows)}")
    print(f"Primeira data: {first_date} | close: {first_close:.2f}")
    print(f"Última data: {last_date} | close: {last_close:.2f}")
    print(f"Retorno do índice no arquivo: {total_return:.2%}")


if __name__ == "__main__":
    main()
