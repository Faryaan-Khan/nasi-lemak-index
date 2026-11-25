"""Tests on the Phase 5 result tables made by sql/04_insights.sql.

Run (PowerShell):  .\\.venv\\Scripts\\python.exe -m pytest
"""

from pathlib import Path

import duckdb
import pytest

MARTS = Path(__file__).resolve().parents[1] / "data" / "marts"
CON = duckdb.connect()

pytestmark = pytest.mark.skipif(
    not (MARTS / "insight_festive_rise.csv").exists(), reason="run src/build.py first"
)


def rows(sql: str):
    return CON.execute(sql).fetchall()


def path(name: str) -> str:
    return (MARTS / name).as_posix()


@pytest.mark.parametrize("name", ["insight_basket_state_quarter.csv", "insight_basket_district_quarter.csv"])
def test_basket_rankings_start_at_zero_gap(name):
    # In each basket the cheapest place is rank 1 and has RM 0 above the cheapest.
    bad = rows(f"SELECT basket FROM '{path(name)}' WHERE rank_cheapest = 1 AND rm_above_cheapest <> 0")
    assert bad == []
    assert rows(f"SELECT COUNT(DISTINCT basket) FROM '{path(name)}'")[0][0] == 3


def test_festive_net_rise_is_rise_minus_placebo():
    bad = rows(
        f"SELECT item FROM '{path('insight_festive_rise.csv')}' "
        "WHERE abs(net_rise_pct - (avg_rise_pct - placebo_rise_pct)) > 0.15"
    )
    assert bad == []


def test_festive_rows_meet_the_evidence_bar():
    low = rows(f"SELECT COUNT(*) FROM '{path('insight_festive_rise.csv')}' WHERE years < 3 OR min_shops < 100")[0][0]
    assert low == 0


def test_storetype_premium_has_enough_pairs_and_no_supermarket_row():
    rows_ = rows(f"SELECT premise_type, pairs FROM '{path('insight_storetype_premium.csv')}'")
    assert rows_ and all(pairs >= 200 for _, pairs in rows_)
    assert all(ptype != "Pasar Raya / Supermarket" for ptype, _ in rows_)


def test_east_west_items_are_compared_like_for_like():
    bad = rows(
        f"SELECT COUNT(*) FROM '{path('insight_east_west_item.csv')}' "
        "WHERE east_states < 2 OR peninsular_states < 8"
    )[0][0]
    assert bad == 0
