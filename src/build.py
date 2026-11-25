"""Run every SQL file in sql/ in order (01_..., 02_..., ...) with DuckDB.

The SQL files use paths relative to the project folder (e.g. 'data/raw/...'), so this script
switches to the project folder first.

Run (PowerShell):
    .\\.venv\\Scripts\\python.exe src\\build.py
"""

import os
import time
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql"


def main() -> None:
    os.chdir(PROJECT_ROOT)
    (PROJECT_ROOT / "data" / "staging").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "data" / "marts").mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()  # in-memory: all results are written out as parquet/csv files
    # Safety limits. When a query needs more memory than the computer has, DuckDB writes
    # temporary files to disk. Cap that at 20 GB so a heavy query fails cleanly instead of
    # filling the whole disk (this happened once, see docs/notes.md, Phase 4).
    con.execute("SET max_temp_directory_size = '20GiB'")
    # We never rely on row order inside a query, so let DuckDB skip keeping it (saves memory).
    con.execute("SET preserve_insertion_order = false")
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        start = time.perf_counter()
        print(f"Running {sql_file.name} ...", end=" ", flush=True)
        con.execute(sql_file.read_text(encoding="utf-8"))
        print(f"done in {time.perf_counter() - start:.1f}s")


if __name__ == "__main__":
    main()
