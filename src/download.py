"""Download PriceCatcher lookups and monthly price files into data/raw/.

How "only fetch what's new" works
---------------------------------
For every file we first ask the server for its ETag (a fingerprint that changes whenever the
file changes) using a cheap HEAD request. We remember the ETag of each file we saved in
data/raw/_manifest.json. If the remote ETag matches what we saved, we skip the download.
data.gov.my adds new days to the current month's file every day, so that file's ETag changes
and it gets re-downloaded; finished months never change, so they are skipped.

Downloads are written to a ".part" file first and renamed only when complete, so a run that is
interrupted never leaves a half-written parquet behind (that's what makes it resumable).

Run (PowerShell):
    .\\.venv\\Scripts\\python.exe src\\download.py              # last 24 months (default)
    .\\.venv\\Scripts\\python.exe src\\download.py --months 6   # last 6 months
    .\\.venv\\Scripts\\python.exe src\\download.py --all        # everything since 2022-01
"""

import argparse
import json
from datetime import date
from pathlib import Path

import duckdb
import requests

BASE_URL = "https://storage.data.gov.my/pricecatcher"
FIRST_MONTH = date(2022, 1, 1)  # PriceCatcher parquet files start in January 2022
LOOKUPS = ["lookup_item", "lookup_premise"]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "_manifest.json"
COVERAGE_PATH = PROJECT_ROOT / "data" / "marts" / "coverage_monthly.csv"


def month_list(n_months: int | None, today: date | None = None) -> list[str]:
    """Return 'YYYY-MM' strings, oldest first, ending with the current month.

    n_months=None means every month since FIRST_MONTH.
    """
    today = today or date.today()
    months = []
    year, month = today.year, today.month
    while (year, month) >= (FIRST_MONTH.year, FIRST_MONTH.month):
        months.append(f"{year:04d}-{month:02d}")
        if n_months is not None and len(months) == n_months:
            break
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return list(reversed(months))


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True))


def remote_etag(session: requests.Session, url: str) -> str | None:
    """ETag of the remote file, or None if it doesn't exist (e.g. a month not published yet)."""
    response = session.head(url, timeout=60)
    if response.status_code == 404 or response.status_code == 403:
        return None
    response.raise_for_status()
    return response.headers.get("ETag", "").strip('"')


def download_file(session: requests.Session, url: str, target: Path) -> None:
    """Stream the file to target.part, then rename to target once it's complete."""
    part = target.with_suffix(target.suffix + ".part")
    with session.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with part.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
    part.replace(target)


def fetch(session: requests.Session, name: str, manifest: dict) -> str:
    """Download one file if it is new or changed. Returns 'new', 'updated', 'skipped' or 'missing'."""
    url = f"{BASE_URL}/{name}.parquet"
    target = RAW_DIR / f"{name}.parquet"
    etag = remote_etag(session, url)
    if etag is None:
        return "missing"
    if target.exists() and manifest.get(name) == etag:
        return "skipped"
    status = "updated" if target.exists() else "new"
    download_file(session, url, target)
    manifest[name] = etag
    save_manifest(manifest)  # save after every file so an interrupted run keeps its progress
    return status


def month_stats(con: duckdb.DuckDBPyConnection, path: Path) -> tuple:
    """Row count and date coverage of one local monthly file."""
    return con.execute(
        "SELECT COUNT(*), MIN(date), MAX(date), COUNT(DISTINCT date) FROM read_parquet(?)",
        [str(path)],
    ).fetchone()


def write_coverage(con: duckdb.DuckDBPyConnection) -> None:
    """Write a small table (one row per month) describing every monthly file we have locally.

    This is committed to git, so the GitHub page always shows how fresh the data is.
    """
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    files = str(RAW_DIR / "pricecatcher_*.parquet").replace("\\", "/")
    con.execute(
        f"""
        COPY (
            SELECT strftime(date, '%Y-%m')     AS month,
                   COUNT(*)                    AS rows,
                   MIN(date)                   AS first_date,
                   MAX(date)                   AS last_date,
                   COUNT(DISTINCT date)        AS days_with_data,
                   COUNT(DISTINCT item_code)   AS items,
                   COUNT(DISTINCT premise_code) AS premises
            FROM read_parquet('{files}')
            GROUP BY 1
            ORDER BY 1
        ) TO '{COVERAGE_PATH.as_posix()}' (HEADER, DELIMITER ',')
        """
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Download PriceCatcher data into data/raw/")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--months", type=int, default=24, help="how many recent months (default 24)")
    group.add_argument("--all", action="store_true", help="download every month since 2022-01")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    months = month_list(None if args.all else args.months)
    con = duckdb.connect()

    with requests.Session() as session:
        print("Lookups:")
        for name in LOOKUPS:
            print(f"  {name:<16} {fetch(session, name, manifest)}")

        print(f"\nMonthly price files ({months[0]} to {months[-1]}):")
        print(f"  {'month':<8} {'status':<8} {'size_MB':>8} {'rows':>11}  dates")
        total_rows = 0
        for i, month in enumerate(months, start=1):
            name = f"pricecatcher_{month}"
            status = fetch(session, name, manifest)
            path = RAW_DIR / f"{name}.parquet"
            if status == "missing":
                print(f"  {month:<8} {'missing':<8}   (not published yet)")
                continue
            rows, first, last, days = month_stats(con, path)
            total_rows += rows
            size_mb = path.stat().st_size / 1_000_000
            print(
                f"  {month:<8} {status:<8} {size_mb:>8.1f} {rows:>11,}  "
                f"{first} to {last} ({days} days)  [{i}/{len(months)}]"
            )

    write_coverage(con)
    print(f"\nTotal rows across these months: {total_rows:,}")
    print(f"Coverage table written to {COVERAGE_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
