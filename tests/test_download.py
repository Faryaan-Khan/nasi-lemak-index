"""Tests for the month-list logic in src/download.py (no network needed).

Run (PowerShell):  .\\.venv\\Scripts\\python.exe -m pytest
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from download import month_list  # noqa: E402


def test_last_three_months_crossing_new_year():
    assert month_list(3, today=date(2026, 1, 15)) == ["2025-11", "2025-12", "2026-01"]


def test_all_months_starts_in_january_2022():
    months = month_list(None, today=date(2026, 11, 24))
    assert months[0] == "2022-01"
    assert months[-1] == "2026-11"
    assert len(months) == 59  # 12 * 4 years (2022-2025) + 11 months of 2026


def test_never_goes_before_first_month():
    assert month_list(100, today=date(2022, 3, 1)) == ["2022-01", "2022-02", "2022-03"]
