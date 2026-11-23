"""Phase 0 smoke test: can DuckDB read PriceCatcher parquet files straight from data.gov.my?

Run:  .\\.venv\\Scripts\\python.exe src\\check_remote.py

It prints the schema and row count of both lookup tables and one monthly price file,
without downloading anything to disk (DuckDB streams the file over HTTPS).
"""

import duckdb

BASE = "https://storage.data.gov.my/pricecatcher"
FILES = {
    "lookup_item": f"{BASE}/lookup_item.parquet",
    "lookup_premise": f"{BASE}/lookup_premise.parquet",
    "pricecatcher_2026-10": f"{BASE}/pricecatcher_2026-10.parquet",
}


def main() -> None:
    con = duckdb.connect()  # in-memory database
    con.execute("INSTALL httpfs; LOAD httpfs;")  # lets DuckDB read https:// URLs

    for name, url in FILES.items():
        print(f"\n=== {name} ===")
        schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()
        for col_name, col_type, *_ in schema:
            print(f"  {col_name:<15} {col_type}")
        rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{url}')").fetchone()[0]
        print(f"  rows: {rows:,}")

    # A quick sanity query on the price file: date range and distinct items/premises
    url = FILES["pricecatcher_2026-10"]
    print("\n=== pricecatcher_2026-10 summary ===")
    print(
        con.execute(
            f"""
            SELECT MIN(date) AS first_day, MAX(date) AS last_day,
                   COUNT(DISTINCT item_code) AS items,
                   COUNT(DISTINCT premise_code) AS premises,
                   ROUND(MEDIAN(price), 2) AS median_price
            FROM read_parquet('{url}')
            """
        ).df().to_string(index=False)
    )


if __name__ == "__main__":
    main()
