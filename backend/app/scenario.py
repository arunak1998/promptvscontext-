"""Loads data/scenario.json, the single editable source of the demo's sample data."""

import json
import os
from datetime import date
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def scenario_path() -> Path:
    return Path(os.environ.get("DEMO_SCENARIO_PATH", DATA_DIR / "scenario.json"))


@lru_cache
def load_scenario() -> dict:
    return json.loads(scenario_path().read_text(encoding="utf-8"))


def as_date(text: str) -> date:
    return date.fromisoformat(text)


def fmt_date(d: date) -> str:
    """30 Sep 2026"""
    return f"{d.day} {d.strftime('%b %Y')}"


def snacks_promos(scenario: dict) -> list[dict]:
    """Promos for the analysed category, oldest first."""
    category = scenario["analysis"]["category"]
    promos = [p for p in scenario["promos"] if p["category"] == category]
    return sorted(promos, key=lambda p: p["end_date"])
