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
  with item codes not in the item lookup, and missing days (1â€“9 Oct 2026).

**Interview one-liner**
"I validated the government data source first, then used DuckDB so I could query millions of rows
with plain SQL on a laptop, and I wrote down every data quirk before cleaning anything."

## Phase 1: Download and daily auto-update

**What I did**
- `src/download.py` downloads both lookup tables and the monthly price files into `data/raw/`
  (last 24 months by default, `--all` for everything since January 2022).
- It prints, for each month, whether the file was new, updated or skipped, plus its size, row
  count and date range, and writes a one-row-per-month summary to `data/marts/coverage_monthly.csv`.
- `src/checks.py` checks the downloaded data: lookups not empty, the expected columns, no missing
  or zero prices, and the newest date is less than 14 days old.
- `tests/test_download.py` tests the month-list logic (e.g. crossing New Year).
- `.github/workflows/daily-update.yml` is a GitHub Action that runs every day at 10 pm Malaysia
  time on GitHub's servers: download, tests, checks, then commit the updated summary tables.

**Why these choices**
- **Only fetch what changed.** Before downloading, the script asks the server for each file's
  ETag (a fingerprint that changes whenever the file changes) and compares it with the one saved
  last time in `data/raw/_manifest.json`. Finished months never change, so they are skipped. The
  current month grows every day, so it is re-downloaded. A full 24-month re-run with nothing new takes about 10 seconds.
- **Resumable.** Each file is written as `.part` first and only renamed when complete, and the
  manifest is saved after every file, so an interrupted run just picks up where it stopped.
- **Checks before commit.** If the government data ever arrives broken, the Action fails and
  nothing is committed, so the dashboards never show bad numbers.
- **GitHub Actions** is free for public repos and needs no server of my own. Raw files are kept
  in the Actions cache, not in git, because git is for code and small tables, not 100M rows.

**What I saw (24 Nov 2026 run)**
- 24 months (Dec 2024 to Nov 2026) = **47,365,287 rows**, about 60 MB of parquet on disk.
- Monthly volume fell from ~2.6M rows in early 2025 to ~1.4 to 1.9M in 2026.
- Many months have missing days (e.g. Feb 2026 has 25 of 28 days; Oct 2026 starts on the 10th),
  so later weekly figures need observation counts.
- All checks passed: 0 bad prices, 0 missing keys, latest date 2026-11-24.

**Interview one-liner**
"The pipeline refreshes itself daily on GitHub Actions, downloads only what changed using ETags,
and refuses to publish if data-quality checks fail."
