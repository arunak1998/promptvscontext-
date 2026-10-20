"""Build the demo SQLite database (50 tables) from data/scenario.json.

Deterministic: same scenario.json + same seed -> same database.
Fails loudly (and writes nothing) if the Snacks drop or the decoy numbers miss their calibration range.

Usage (from backend/):  python scripts/seed.py
"""

import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import db_path  # noqa: E402
from app.metrics import window_change  # noqa: E402
from app.scenario import as_date, fmt_date, load_scenario  # noqa: E402

EXPECTED_TABLE_COUNT = 50


def date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def active_promo(promos: list[dict], category: str, day: date) -> dict | None:
    for p in promos:
        if p["category"] == category and as_date(p["start_date"]) <= day <= as_date(p["end_date"]):
            return p
    return None


def noisy(rng: np.random.Generator, value: float, noise_pct: float) -> int:
    return max(0, round(value * (1 + rng.normal(0, noise_pct / 100))))


def build_daily_sales(sc: dict, rng: np.random.Generator) -> pd.DataFrame:
    weekday = sc["weekday_factors_mon_to_sun"]
    days = date_range(as_date(sc["date_range"]["start"]), as_date(sc["date_range"]["end"]))
    rows = []
    for day in days:
        for cat in sc["categories"]:
            promo = active_promo(sc["promos"], cat["name"], day)
            uplift = 1 + (promo["uplift_pct"] / 100 if promo else 0)
            discount = 1 - (promo["discount_pct"] / 100 if promo else 0)
            units = noisy(rng, cat["base_units"] * weekday[day.weekday()] * uplift, cat["noise_pct"])
            rows.append((day.isoformat(), cat["name"], units, round(units * cat["unit_price"] * discount, 2)))
    return pd.DataFrame(rows, columns=["date", "category", "units", "revenue"])


def build_promo_calendar(sc: dict) -> pd.DataFrame:
    cols = ["category", "promo_name", "start_date", "end_date", "discount_pct"]
    return pd.DataFrame([{c: p[c] for c in cols} for p in sc["promos"]], columns=cols)


def category_daily(sales: pd.DataFrame, category: str) -> pd.DataFrame:
    df = sales[sales["category"] == category][["date", "units"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    return df


def build_quarterly_report(sc: dict, sales: pd.DataFrame) -> pd.DataFrame:
    """Report text is written from the computed data, never from hardcoded numbers."""
    window = sc["analysis"]["window_days"]
    promos = {p["promo_name"]: p for p in sc["promos"]}
    rows = []
    for rep in sc["quarterly_reports"]:
        text = rep["template"]
        if "about_promo" in rep:
            promo = promos[rep["about_promo"]]
            end = as_date(promo["end_date"])
            change = window_change(category_daily(sales, promo["category"]), end, window)
            text = text.format(drop_pct=round(change.drop_pct), promo_name=promo["promo_name"], promo_end=fmt_date(end))
        rows.append((rep["quarter"], rep["category"], text))
    return pd.DataFrame(rows, columns=["quarter", "category", "summary_text"])


def build_decoy_sales(sc: dict, rng: np.random.Generator, spec: dict, pivot: date, snacks_after_factor: float) -> pd.DataFrame:
    """Sales-shaped table where Snacks moves by `snacks_after_factor` after `pivot`. Other categories are flat noise."""
    weekday = sc["weekday_factors_mon_to_sun"]
    prices = {c["name"]: c["unit_price"] for c in sc["categories"]}
    scale = {c["name"]: c["base_units"] / sc["categories"][0]["base_units"] for c in sc["categories"]}
    rows = []
    for day in date_range(as_date(spec["start"]), as_date(spec["end"])):
        for cat in prices:
            factor = snacks_after_factor if (cat == sc["analysis"]["category"] and day > pivot) else 1.0
            units = noisy(rng, spec["base_units"] * scale[cat] * weekday[day.weekday()] * factor, spec["noise_pct"])
            rows.append((day.isoformat(), cat, units, round(units * prices[cat], 2)))
    return pd.DataFrame(rows, columns=["date", "category", "units", "revenue"])


def build_small_copy(sc: dict, rng: np.random.Generator, spec: dict) -> pd.DataFrame:
    flat = {"start": spec["start"], "end": spec["end"], "base_units": 400, "noise_pct": 8}
    return build_decoy_sales(sc, rng, flat, as_date(spec["end"]), 1.0)


def fake_value(col: str, i: int, sc: dict, rng: np.random.Generator):
    pools = sc["value_pools"]
    if col in pools:
        return str(rng.choice(pools[col]))
    if col == "category":
        return sc["categories"][i % len(sc["categories"])]["name"]
    if col.endswith("_date"):
        return (date(2026, 1, 1) + timedelta(days=int(rng.integers(0, 288)))).isoformat()
    if col == "month":
        return f"2026-{i % 12 + 1:02d}"
    if col == "quarter":
        return f"Q{i % 4 + 1} 2026"
    if col.endswith("_id"):
        return int(rng.integers(1, 60))
    if any(k in col for k in ("price", "amount", "budget")):
        return round(float(rng.uniform(40, 9000)), 2)
    if col == "rating":
        return round(float(rng.uniform(2.5, 5)), 1)
    if col.endswith("_pct"):
        return int(rng.choice([5, 10, 12, 15, 18, 20]))
    if col == "temp_c":
        return round(float(rng.uniform(24, 38)), 1)
    if col == "rain_mm":
        return round(float(rng.uniform(0, 40)), 1)
    return int(rng.integers(1, 500))


def build_filler(sc: dict, rng: np.random.Generator, spec: dict) -> pd.DataFrame:
    cols = spec["columns"]
    rows = []
    for i in range(spec["rows"]):
        first = i + 1 if cols[0].endswith("_id") else fake_value(cols[0], i, sc, rng)
        rows.append([first] + [fake_value(c, i, sc, rng) for c in cols[1:]])
    return pd.DataFrame(rows, columns=cols)


def check_range(label: str, value: float, bounds: dict) -> None:
    if not bounds["min"] <= value <= bounds["max"]:
        raise SystemExit(
            f"CALIBRATION FAILED: {label} = {value:.2f}%, expected {bounds['min']} to {bounds['max']}.\n"
            "Adjust uplift_pct / noise_pct in data/scenario.json (or the expected range) and run again."
        )
    print(f"  ok  {label}: {value:.2f}%  (expected {bounds['min']} to {bounds['max']})")


def build_tables(sc: dict) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(sc["seed"])
    analysis = sc["analysis"]
    pivot = as_date(analysis["pivot_date"])
    test_spec = sc["decoys"]["sales_test"]
    backup_spec = sc["decoys"]["sales_backup_2023"]

    sales = build_daily_sales(sc, rng)
    tables = {
        "daily_sales": sales,
        "promo_calendar": build_promo_calendar(sc),
        "quarterly_report": build_quarterly_report(sc, sales),
        "sales_test": build_decoy_sales(sc, rng, test_spec, pivot, 1 + test_spec["snacks_change_after_pivot_pct"] / 100),
        "sales_backup_2023": build_decoy_sales(
            sc, rng, backup_spec, as_date(backup_spec["pivot_date"]), 1 - backup_spec["snacks_drop_after_pivot_pct"] / 100
        ),
    }
    for spec in sc["decoys"]["small_copies"]:
        tables[spec["name"]] = build_small_copy(sc, rng, spec)
    for spec in sc["filler_tables"]:
        tables[spec["name"]] = build_filler(sc, rng, spec)
    return tables


def check_calibration(sc: dict, tables: dict[str, pd.DataFrame]) -> None:
    analysis = sc["analysis"]
    cat, window = analysis["category"], analysis["window_days"]
    backup_spec = sc["decoys"]["sales_backup_2023"]

    if len(tables) != EXPECTED_TABLE_COUNT:
        raise SystemExit(f"CALIBRATION FAILED: built {len(tables)} tables, expected {EXPECTED_TABLE_COUNT}.")
    print(f"  ok  {len(tables)} tables")

    real = window_change(category_daily(tables["daily_sales"], cat), as_date(analysis["pivot_date"]), window)
    check_range(f"{cat} drop in daily_sales", real.drop_pct, analysis["expected_drop_pct"])

    test = window_change(category_daily(tables["sales_test"], cat), as_date(analysis["pivot_date"]), window)
    check_range(f"{cat} change in sales_test", test.change_pct, sc["decoys"]["sales_test"]["expected_change_pct"])

    backup = window_change(category_daily(tables["sales_backup_2023"], cat), as_date(backup_spec["pivot_date"]), window)
    check_range(f"{cat} drop in sales_backup_2023", backup.drop_pct, backup_spec["expected_drop_pct"])


def write_db(tables: dict[str, pd.DataFrame], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    with sqlite3.connect(tmp) as conn:
        for name, df in tables.items():
            df.to_sql(name, conn, index=False)
    tmp.replace(path)


def main() -> None:
    sc = load_scenario()
    print("Building tables from scenario.json ...")
    tables = build_tables(sc)
    check_calibration(sc, tables)
    write_db(tables, db_path())
    print(f"Wrote {db_path()}")


if __name__ == "__main__":
    main()
