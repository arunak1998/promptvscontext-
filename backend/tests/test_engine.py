from contextlib import closing

import pytest

from app.db import connect, read_sql
from app.engine import DECOY_TABLES, category_daily, run_stage
from app.metrics import window_change
from app.scenario import as_date, fmt_date


def real_promo_drop() -> tuple[float, str]:
    """Computed independently of the engine: latest ended Snacks promo -> drop after it."""
    with closing(connect()) as conn:
        end = read_sql(
            conn, "SELECT MAX(end_date) AS end_date FROM promo_calendar WHERE category = 'Snacks' AND end_date < '2026-10-15'"
        )["end_date"][0]
        daily = category_daily(conn, "daily_sales", "Snacks")
    return window_change(daily, as_date(end), 30).drop_pct, fmt_date(as_date(end))


def test_stage3_answer_uses_computed_numbers():
    drop, promo_end = real_promo_drop()
    result = run_stage(3)
    assert f"{drop:.1f}%" in result.answer_text
    assert promo_end in result.answer_text
    assert result.badge.label == "Fact"
    assert len(result.context.sources) == 4  # prompt + exactly 3 sources


@pytest.mark.parametrize("trap", ["most_rows", "newest_dates"])
def test_stage4_picks_wrong_table_and_number(trap):
    stage3, stage4 = run_stage(3), run_stage(4, trap)
    assert stage4.wrong_table in DECOY_TABLES
    assert abs(stage4.headline_change_pct - stage3.headline_change_pct) >= 5
    assert len(stage4.context.sources) == 51  # prompt + 50 tables
    assert [s.name for s in stage4.context.sources if s.used and s.kind == "table"] == [stage4.wrong_table]


@pytest.mark.parametrize("stage", [1, 2, 3, 4])
def test_captured_answers_match_current_data(stage):
    assert run_stage(stage).capture_status == "captured"


def test_stale_capture_falls_back_to_engine(tmp_path, monkeypatch):
    stale = tmp_path / "captures.json"
    stale.write_text('{"answers": {"3": {"fingerprint": "old", "model": "x", "answer_text": "old answer"}}}')
    monkeypatch.setenv("DEMO_CAPTURES_PATH", str(stale))
    result = run_stage(3)
    assert result.capture_status == "stale"
    assert result.answer_source == "engine"
    assert "old answer" not in result.answer_text
