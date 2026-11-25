"""Phase 6: forecast the national weekly median price of 5 key items, 8 weeks ahead.

Plain-language summary
----------------------
1. Take each item's national weekly median price (data/marts/item_national_week.csv).
2. Compare four simple models by "backtesting": pretend it's an earlier week, forecast the next
   8 weeks, then check against what really happened. Do this from every week in the last year.
     - naive          : next weeks = this week's price            (prices are sticky)
     - seasonal_naive : next weeks = the same week last year     (the CLAUDE.md baseline)
     - ets            : exponential smoothing with a damped trend (statsmodels ETSModel)
     - holt_winters   : exponential smoothing with a damped trend + yearly seasonality
3. Score each model with MAPE (mean absolute percentage error: on average, how many % off).
4. Forecast the next 8 weeks with every model, and mark the one with the lowest backtest MAPE.
5. Uncertainty band (80%): taken from the model's own backtest errors at each horizon, i.e.
   "in 8 out of 10 past forecasts this far ahead, the real price fell inside this range".

Run (PowerShell):
    .\\.venv\\Scripts\\python.exe src\\forecast.py

Outputs (data/marts/):
    forecast_accuracy.csv   backtest MAPE per item, model and horizon (1-8 weeks) + overall
    forecast_item_week.csv  last 52 weeks of actual prices + 8 weeks of forecasts with 80% bands
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.holtwinters import ExponentialSmoothing

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MARTS = PROJECT_ROOT / "data" / "marts"

ITEMS = {
    1: "Chicken (standard, 1 kg)",
    1110: "Eggs, grade B (30)",
    904: "Rice, Cap Rambutan 5% (10 kg)",
    1440: "Big onion, India (1 kg)",
    94: "Red chilli (1 kg)",
}
HORIZON = 8           # weeks ahead
BACKTEST_WEEKS = 52   # forecast origins: every week of the last year
SEASON = 52           # weeks in a year
MODELS = ["naive", "seasonal_naive", "ets", "holt_winters"]

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def load_series(item_code: int, weekly: pd.DataFrame) -> pd.Series:
    """Weekly national median for one item, complete weeks only, gaps filled by interpolation."""
    s = weekly[weekly.item_code == item_code].set_index("week_start")["median_price"].sort_index()
    complete = weekly[weekly.item_code == item_code].set_index("week_start")["n_days"].sort_index()
    # Drop the first and last week if they are partial (fewer than 4 days of data).
    if complete.iloc[0] < 4:
        s = s.iloc[1:]
    if complete.iloc[-1] < 4:
        s = s.iloc[:-1]
    full_index = pd.date_range(s.index.min(), s.index.max(), freq="W-MON")
    s = s.reindex(full_index).interpolate(method="linear")  # a few missing weeks (rice) are filled
    s.index.name = "week_start"
    return s.astype(float)


def forecast(history: pd.Series, model: str, h: int = HORIZON) -> np.ndarray:
    """Forecast h weeks after the end of `history` with one of the four models."""
    y = history.to_numpy()
    if model == "naive":
        return np.repeat(y[-1], h)
    if model == "seasonal_naive":
        # the same week one year earlier, for each of the next h weeks
        return np.array([y[len(y) - SEASON + i] for i in range(h)])
    if model == "ets":
        fit = ETSModel(history.reset_index(drop=True), error="add", trend="add", damped_trend=True).fit(disp=False)
        return np.asarray(fit.forecast(h))
    if model == "holt_winters":
        fit = ExponentialSmoothing(
            history.reset_index(drop=True), trend="add", damped_trend=True,
            seasonal="add", seasonal_periods=SEASON, initialization_method="estimated",
        ).fit()
        return np.asarray(fit.forecast(h))
    raise ValueError(model)


def backtest(series: pd.Series) -> pd.DataFrame:
    """Forecast from each of the last BACKTEST_WEEKS origins and record the errors."""
    rows = []
    last_origin = len(series) - HORIZON          # the last origin whose 8 weeks are all known
    for origin in range(last_origin - BACKTEST_WEEKS + 1, last_origin + 1):
        history, future = series.iloc[:origin], series.iloc[origin:origin + HORIZON].to_numpy()
        for model in MODELS:
            pred = forecast(history, model)
            for step in range(HORIZON):
                rows.append({
                    "model": model, "horizon": step + 1,
                    "actual": future[step], "forecast": pred[step],
                })
    out = pd.DataFrame(rows)
    out["ape"] = (out.forecast - out.actual).abs() / out.actual * 100   # absolute % error
    out["ratio"] = out.actual / out.forecast                             # for the 80% band
    return out


def main() -> None:
    weekly = pd.read_csv(MARTS / "item_national_week.csv", parse_dates=["week_start"])
    accuracy_rows, output_rows = [], []

    for item_code, label in ITEMS.items():
        series = load_series(item_code, weekly)
        print(f"{label}: {len(series)} weeks, {series.index.min().date()} to {series.index.max().date()}")

        bt = backtest(series)
        by_h = bt.groupby(["model", "horizon"]).agg(mape=("ape", "mean"), n=("ape", "size")).reset_index()
        overall = bt.groupby("model").agg(mape=("ape", "mean"), n=("ape", "size")).reset_index()
        overall["horizon"] = "1-8"
        best_model = overall.sort_values(["mape", "model"]).iloc[0]["model"]

        acc = pd.concat([by_h.astype({"horizon": str}), overall])
        acc.insert(0, "item", label)
        acc.insert(0, "item_code", item_code)
        acc["is_best"] = acc.model == best_model
        accuracy_rows.append(acc)

        # Recent actual prices, for the chart
        recent = series.iloc[-52:]
        for week, value in recent.items():
            output_rows.append({"item_code": item_code, "item": label, "week_start": week.date(),
                                "kind": "actual", "model": "", "price": value,
                                "low_80": None, "high_80": None, "is_best": None})

        # Next 8 weeks from every model, with an 80% band from its own backtest errors
        future_weeks = pd.date_range(series.index.max() + pd.Timedelta(weeks=1), periods=HORIZON, freq="W-MON")
        for model in MODELS:
            pred = forecast(series, model)
            ratios = bt[bt.model == model].groupby("horizon")["ratio"]
            lo, hi = ratios.quantile(0.10), ratios.quantile(0.90)
            for step, week in enumerate(future_weeks, start=1):
                output_rows.append({"item_code": item_code, "item": label, "week_start": week.date(),
                                    "kind": "forecast", "model": model, "price": pred[step - 1],
                                    "low_80": pred[step - 1] * lo[step], "high_80": pred[step - 1] * hi[step],
                                    "is_best": model == best_model})

        print(overall.sort_values("mape").round(2).to_string(index=False))
        print(f"  best: {best_model}\n")

    accuracy = pd.concat(accuracy_rows)
    accuracy["mape"] = accuracy.mape.round(2)
    accuracy.to_csv(MARTS / "forecast_accuracy.csv", index=False)

    out = pd.DataFrame(output_rows)
    for col in ["price", "low_80", "high_80"]:
        out[col] = out[col].astype(float).round(2)
    out.to_csv(MARTS / "forecast_item_week.csv", index=False)
    print("Wrote data/marts/forecast_accuracy.csv and data/marts/forecast_item_week.csv")


if __name__ == "__main__":
    main()
