"""Data-quality checks on the downloaded raw files.

The daily GitHub Action runs this after downloading. If any check fails, the script exits
with an error, the Action stops, and nothing gets committed, so bad data never reaches the
dashboards.

Run (PowerShell):
    .\\.venv\\Scripts\\python.exe src\\checks.py
"""

import sys
from datetime import date
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
MAX_DAYS_STALE = 14  # data.gov.my has had gaps of ~9 days, so allow some slack


def run_checks() -> list[str]:
    """Return a list of failure messages (empty list = all good)."""
    failures = []
    con = duckdb.connect()
    prices = (RAW_DIR / "pricecatcher_*.parquet").as_posix()

    # 1. Both lookups exist and have rows
    for name in ["lookup_item", "lookup_premise"]:
        path = RAW_DIR / f"{name}.parquet"
        if not path.exists():
            failures.append(f"{name}.parquet is missing")
            continue
        rows = con.execute("SELECT COUNT(*) FROM read_parquet(?)", [str(path)]).fetchone()[0]
        print(f"  {name}: {rows:,} rows")
        if rows == 0:
            failures.append(f"{name}.parquet is empty")

    if not list(RAW_DIR.glob("pricecatcher_*.parquet")):
        return failures + ["no monthly price files found"]

    # 2. Price files have the expected columns
    columns = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{prices}')").fetchall()]
    expected = ["date", "premise_code", "item_code", "price"]
    print(f"  columns: {columns}")
    if columns != expected:
        failures.append(f"price files have columns {columns}, expected {expected}")
        return failures

    # 3. No missing or non-positive prices, no missing keys
    bad = con.execute(
        f"""
        SELECT COUNT(*) FILTER (WHERE price IS NULL OR price <= 0),
               COUNT(*) FILTER (WHERE date IS NULL OR item_code IS NULL OR premise_code IS NULL),
               COUNT(*), CAST(MAX(date) AS DATE)  -- 2022 files store date as TIMESTAMP
        FROM read_parquet('{prices}')
        """
    ).fetchone()
    bad_prices, bad_keys, total, latest = bad
    print(f"  total rows: {total:,} | bad prices: {bad_prices:,} | missing keys: {bad_keys:,}")
    if bad_prices:
        failures.append(f"{bad_prices:,} rows with a missing or non-positive price")
    if bad_keys:
        failures.append(f"{bad_keys:,} rows with a missing date/item/premise")

    # 4. Data is fresh: latest date is recent
    days_old = (date.today() - latest).days
    print(f"  latest date: {latest} ({days_old} days ago)")
    if days_old > MAX_DAYS_STALE:
        failures.append(f"latest data is {days_old} days old (limit {MAX_DAYS_STALE})")

    return failures


def main() -> None:
    print("Running data checks:")
    failures = run_checks()
    if failures:
        print("\nFAILED:")
        for message in failures:
            print(f"  - {message}")
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
