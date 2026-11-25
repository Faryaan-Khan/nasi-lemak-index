"""Tests for the hand-made reference files (baskets, festive calendar) and the tables built
from them by sql/03_baskets_festive.sql.

Run (PowerShell):  .\\.venv\\Scripts\\python.exe -m pytest
"""

from datetime import date
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "data" / "reference"
MARTS = ROOT / "data" / "marts"
LOOKUP = ROOT / "data" / "raw" / "lookup_item.parquet"
CON = duckdb.connect()


def rows(sql: str):
    return CON.execute(sql).fetchall()


def p(path: Path) -> str:
    return path.as_posix()


# --- festive calendar (no data download needed) ------------------------------------------

def test_every_festival_has_one_date_per_year_2022_to_2027():
    counts = rows(f"SELECT festival, COUNT(DISTINCT year) FROM read_csv('{p(REF / 'festive_calendar.csv')}') GROUP BY 1")
    assert dict(counts) == {"Chinese New Year": 6, "Hari Raya Aidilfitri": 6, "Deepavali": 6}


def test_festival_dates_match_their_year_and_have_a_source():
    for festival, year, day, source in rows(
        f"SELECT festival, year, CAST(date AS DATE), source FROM read_csv('{p(REF / 'festive_calendar.csv')}')"
    ):
        assert day.year == year, festival
        assert source and len(source) > 10, f"{festival} {year} has no source"


def test_known_official_dates():
    # Spot checks against the JPM federal holiday schedules (kabinet.gov.my)
    got = {(f, y): d for f, y, d in rows(
        f"SELECT festival, year, CAST(date AS DATE) FROM read_csv('{p(REF / 'festive_calendar.csv')}')")}
    assert got[("Chinese New Year", 2026)] == date(2026, 2, 17)
    assert got[("Hari Raya Aidilfitri", 2026)] == date(2026, 3, 21)
    assert got[("Deepavali", 2025)] == date(2025, 10, 20)


# --- baskets -----------------------------------------------------------------------------

@pytest.mark.skipif(not LOOKUP.exists(), reason="run src/download.py first")
def test_basket_items_and_units_match_the_government_lookup():
    mismatches = rows(
        f"""SELECT b.basket, b.item_code FROM read_csv('{p(REF / 'baskets.csv')}', header = true) b
            LEFT JOIN '{p(LOOKUP)}' i USING (item_code)
            WHERE i.item IS DISTINCT FROM b.item OR i.unit IS DISTINCT FROM b.unit"""
    )
    assert mismatches == []


def test_basket_quantities_positive_and_no_duplicate_items():
    bad = rows(f"SELECT * FROM read_csv('{p(REF / 'baskets.csv')}', header = true) WHERE quantity <= 0")
    dupes = rows(
        f"SELECT basket, item_code FROM read_csv('{p(REF / 'baskets.csv')}', header = true) "
        "GROUP BY ALL HAVING COUNT(*) > 1"
    )
    assert bad == [] and dupes == []


# --- tables built from them --------------------------------------------------------------

built = pytest.mark.skipif(not (MARTS / "festive_window.csv").exists(), reason="run src/build.py first")


@built
@pytest.mark.parametrize("name", ["basket_cost_national_week.csv", "basket_cost_state_week.csv",
                                  "basket_cost_district_week.parquet"])
def test_basket_costs_only_for_complete_baskets(name):
    incomplete = rows(
        f"""SELECT COUNT(*) FROM '{p(MARTS / name)}' c
            JOIN (SELECT basket, COUNT(*) n FROM read_csv('{p(REF / 'baskets.csv')}', header = true) GROUP BY 1) s
            USING (basket) WHERE c.items_priced <> s.n OR c.basket_cost <= 0"""
    )[0][0]
    assert incomplete == 0


@built
def test_festive_index_is_100_around_the_baseline():
    # The baseline is the median of weeks -12..-9, so the median index in those weeks must be ~100.
    med = rows(f"SELECT median(price_index) FROM '{p(MARTS / 'festive_window.csv')}' WHERE week_offset BETWEEN -12 AND -9")[0][0]
    assert 99 <= med <= 101


@built
def test_festive_window_offsets_in_range():
    lo, hi = rows(f"SELECT MIN(week_offset), MAX(week_offset) FROM '{p(MARTS / 'festive_window.csv')}'")[0]
    assert lo == -12 and hi <= 2
