"""Tests on the forecast outputs made by src/forecast.py.

Run (PowerShell):  .\\.venv\\Scripts\\python.exe -m pytest
"""

from pathlib import Path

import pandas as pd
import pytest

MARTS = Path(__file__).resolve().parents[1] / "data" / "marts"
FORECAST = MARTS / "forecast_item_week.csv"
ACCURACY = MARTS / "forecast_accuracy.csv"

pytestmark = pytest.mark.skipif(not FORECAST.exists(), reason="run src/forecast.py first")
MODELS = {"naive", "seasonal_naive", "ets", "holt_winters"}


@pytest.fixture(scope="module")
def fc():
    return pd.read_csv(FORECAST, parse_dates=["week_start"])


@pytest.fixture(scope="module")
def acc():
    return pd.read_csv(ACCURACY, dtype={"horizon": str})


def test_five_items_each_with_8_weeks_from_every_model(fc):
    f = fc[fc.kind == "forecast"]
    assert f.item_code.nunique() == 5
    counts = f.groupby(["item_code", "model"]).size()
    assert set(f.model) == MODELS and (counts == 8).all()


def test_forecast_starts_the_week_after_the_last_actual(fc):
    for _, g in fc.groupby("item_code"):
        last_actual = g[g.kind == "actual"].week_start.max()
        first_forecast = g[g.kind == "forecast"].week_start.min()
        assert first_forecast - last_actual == pd.Timedelta(weeks=1)


def test_bands_are_ordered_and_prices_positive(fc):
    f = fc[fc.kind == "forecast"]
    assert (f.price > 0).all()
    assert (f.low_80 <= f.high_80).all()


def test_one_best_model_per_item_and_it_has_the_lowest_mape(acc):
    overall = acc[acc.horizon == "1-8"]
    for _, g in overall.groupby("item_code"):
        assert g.is_best.sum() == 1
        assert g[g.is_best].mape.iloc[0] == g.mape.min()


def test_backtest_covers_every_horizon(acc):
    by_h = acc[acc.horizon != "1-8"]
    assert set(by_h.horizon.astype(int)) == set(range(1, 9))
    assert (acc.mape >= 0).all()
