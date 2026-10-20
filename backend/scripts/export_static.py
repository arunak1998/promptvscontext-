"""Snapshot every API response into frontend/public/data/*.json so the frontend runs with no backend (e.g. on Vercel).

Usage (from backend/):  python scripts/export_static.py
Run it again after changing scenario.json or the captured answers.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine import run_stage  # noqa: E402
from app.main import get_dataset, get_question, get_tables  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "data"


def write(name: str, model) -> None:
    (OUT / name).write_text(json.dumps(model.model_dump(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {name}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write("question.json", get_question())
    write("tables.json", get_tables())
    write("dataset.json", get_dataset())
    for stage in (1, 2, 3):
        write(f"run-{stage}.json", run_stage(stage))
    for trap in ("most_rows", "newest_dates"):
        write(f"run-4-{trap}.json", run_stage(4, trap))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
