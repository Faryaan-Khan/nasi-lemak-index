"""Tests on the summary tables made by sql/02_marts.sql.

Skipped automatically if the marts haven't been built yet (run src/build.py).

Run (PowerShell):  .\\.venv\\Scripts\\python.exe -m pytest
"""

from pathlib import Path

import duckdb
import pytest

MARTS = Path(__file__).resolve().parents[1] / "data" / "marts"
MIN_SHOPS = 3

# table name -> the columns that should identify one row
TABLES = {
    "item_national_week.csv": ["item_code", "week_start"],
    "item_state_week.parquet": ["item_code", "state", "week_start"],
    "item_district_week.parquet": ["item_code", "state", "district", "week_start"],
    "item_premisetype_district_month.parquet": ["item_code", "premise_type", "state", "district", "month"],
}

pytestmark = pytest.mark.skipif(
    not (MARTS / "item_district_week.parquet").exists(), reason="run src/build.py first"
)


def path(name: str) -> str:
    return (MARTS / name).as_posix()


CON = duckdb.connect()


def one(sql: str):
    return CON.execute(sql).fetchone()[0]


@pytest.mark.parametrize("name, keys", TABLES.items())
def test_one_row_per_key(name, keys):
    cols = ", ".join(keys)
    dupes = one(f"SELECT COUNT(*) FROM (SELECT {cols} FROM '{path(name)}' GROUP BY ALL HAVING COUNT(*) > 1)")
    assert dupes == 0


@pytest.mark.parametrize("name", TABLES)
def test_every_figure_backed_by_enough_shops(name):
    assert one(f"SELECT MIN(n_shops) FROM '{path(name)}'") >= MIN_SHOPS


@pytest.mark.parametrize("name", TABLES)
def test_prices_are_positive_and_present(name):
    assert one(f"SELECT COUNT(*) FROM '{path(name)}' WHERE median_price IS NULL OR median_price <= 0") == 0


@pytest.mark.parametrize("name", TABLES)
def test_every_item_has_a_name(name):
    missing = one(
        f"SELECT COUNT(*) FROM '{path(name)}' WHERE item_code NOT IN "
        f"(SELECT item_code FROM '{path('dim_item.csv')}')"
    )
    assert missing == 0


def test_districts_match_lookup():
    missing = one(
        f"SELECT COUNT(*) FROM (SELECT DISTINCT state, district FROM '{path('item_district_week.parquet')}') "
        f"ANTI JOIN '{path('dim_district.csv')}' USING (state, district)"
    )
    assert missing == 0


def test_national_quantiles_in_order():
    bad = one(
        f"SELECT COUNT(*) FROM '{path('item_national_week.csv')}' "
        "WHERE NOT (p25_price <= median_price AND median_price <= p75_price)"
    )
    assert bad == 0
