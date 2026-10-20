"""The one calculation the whole demo is about: average daily units before vs after a date."""

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd


@dataclass(frozen=True)
class WindowChange:
    pivot: date
    before_avg: float
    after_avg: float
    before_days: int
    after_days: int

    @property
    def change_pct(self) -> float:
        return (self.after_avg - self.before_avg) / self.before_avg * 100

    @property
    def drop_pct(self) -> float:
        return -self.change_pct


def window_change(daily: pd.DataFrame, pivot: date, window_days: int) -> WindowChange:
    """Compare average daily units in the `window_days` up to `pivot` with the `window_days` after it.

    `daily` needs a `date` column (datetime64) and a `units` column, one row per day.
    The after-window only uses days that exist in the data.
    """
    pivot_ts = pd.Timestamp(pivot)
    before = daily[(daily["date"] > pivot_ts - timedelta(days=window_days)) & (daily["date"] <= pivot_ts)]
    after = daily[(daily["date"] > pivot_ts) & (daily["date"] <= pivot_ts + timedelta(days=window_days))]
    if before.empty or after.empty:
        raise ValueError(f"Not enough data around {pivot} to compare windows")
    return WindowChange(
        pivot=pivot,
        before_avg=float(before["units"].mean()),
        after_avg=float(after["units"].mean()),
        before_days=len(before),
        after_days=len(after),
    )
