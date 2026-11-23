# Project notes (plain language, for interviews)

## Phase 0: Setup

**What I did**
- Created the folder layout (`data/`, `sql/`, `src/`, `docs/`, `dashboard/`, `app/`, `tests/`).
- Made a Python virtual environment (`.venv`) and a `requirements.txt` with DuckDB, pandas,
  pyarrow, requests, statsmodels, jupyter, matplotlib and pytest.
- Added a `.gitignore` so the big raw data, the venv and any secrets never get committed.
- Wrote `src/check_remote.py`, a smoke test where DuckDB reads PriceCatcher parquet files straight
  over HTTPS without downloading them first.
- Documented the schema and the first data quirks in `docs/schema.md`.

**Why these choices**
- **DuckDB** is a database that runs inside Python with no server to install. It can run SQL
  directly on parquet files, which is perfect for ~100M rows on a laptop. pandas would need the
  whole dataset in memory; DuckDB only reads the columns and rows a query needs.
- **Parquet** is a compressed, column-based file format. A month of ~1.4M prices is only ~2 MB.
- **A venv** keeps this project's library versions separate from anything else on my machine, so
  anyone can rebuild the same setup from `requirements.txt`.

**What I checked**
- The URL pattern in CLAUDE.md is correct: lookups and monthly files from 2022-01 to 2026-11 all
  respond.
- DuckDB read 1,359,706 rows for October 2026 and summarised them in seconds.
- Early quirks: placeholder `-1` codes, a `Pasar Basah ` value with a trailing space, ~1.5% of rows
  with item codes not in the item lookup, and missing days (1–9 Oct 2026).

**Interview one-liner**
"I validated the government data source first, then used DuckDB so I could query millions of rows
with plain SQL on a laptop, and I wrote down every data quirk before cleaning anything."
