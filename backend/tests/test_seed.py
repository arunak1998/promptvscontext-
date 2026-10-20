from contextlib import closing

import seed
from app.db import connect, list_tables
from app.engine import category_daily
from app.metrics import window_change
from app.scenario import as_date, load_scenario


def test_snacks_drop_is_calibrated():
    sc = load_scenario()
    with closing(connect()) as conn:
        daily = category_daily(conn, "daily_sales", "Snacks")
    change = window_change(daily, as_date(sc["analysis"]["pivot_date"]), 30)
    assert 17.5 <= change.drop_pct <= 18.5


def test_database_has_50_tables():
    with closing(connect()) as conn:
        assert len(list_tables(conn)) == 50


def test_seed_is_deterministic():
    sc = load_scenario()
    first, second = seed.build_tables(sc), seed.build_tables(sc)
    assert all(first[name].equals(second[name]) for name in first)
