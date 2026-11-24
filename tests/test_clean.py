"""Data-quality tests on the cleaned table made by sql/01_clean.sql.

They are skipped automatically if data/staging/prices_clean.parquet doesn't exist yet
(run src/download.py and src/build.py first).

Run (PowerShell):  .\\.venv\\Scripts\\python.exe -m pytest
"""

from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "staging" / "prices_clean.parquet"
RAW = (ROOT / "data" / "raw" / "pricecatcher_*.parquet").as_posix()

pytestmark = pytest.mark.skipif(not CLEAN.exists(), reason="run src/build.py first")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute(f"CREATE VIEW clean AS SELECT * FROM read_parquet('{CLEAN.as_posix()}')")
    return c


def one(con, sql):
    return con.execute(sql).fetchone()[0]


def test_no_placeholder_codes(con):
    assert one(con, "SELECT COUNT(*) FROM clean WHERE premise_code <= 0 OR item_code <= 0") == 0


def test_every_row_has_a_known_shop_location(con):
    assert one(con, "SELECT COUNT(*) FROM clean WHERE state IS NULL OR district IS NULL OR premise_type IS NULL") == 0


def test_no_rows_lost_apart_from_placeholder_shops(con):
    raw = one(con, f"SELECT COUNT(*) FROM read_parquet('{RAW}') WHERE premise_code > 0")
    assert one(con, "SELECT COUNT(*) FROM clean") == raw


def test_text_is_trimmed(con):
    untrimmed = one(
        con,
        "SELECT COUNT(*) FROM clean WHERE premise_type <> trim(premise_type) "
        "OR state <> trim(state) OR district <> trim(district) OR item <> trim(item)",
    )
    assert untrimmed == 0


def test_region_split(con):
    east = {r[0] for r in con.execute("SELECT DISTINCT state FROM clean WHERE region = 'East Malaysia'").fetchall()}
    assert east == {"Sabah", "Sarawak", "W.P. Labuan"}


def test_outlier_share_is_small(con):
    # If this jumps, either the data got much worse or the outlier rule broke.
    share = one(con, "SELECT AVG(is_outlier::INT) FROM clean")
    assert share < 0.03


def test_hundredfold_typos_are_flagged(con):
    assert one(con, "SELECT COUNT(*) FROM clean WHERE price_to_median > 50 AND NOT is_outlier") == 0
