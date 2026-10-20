"""Captured AI answers.

Each stage's answer was written once by an AI model from the exact prompt + context the app builds,
then saved in data/captured_answers.json together with a fingerprint of that context.
The app replays them; it never calls a model. If the data changes, the fingerprint no longer
matches, the capture is marked stale and the engine's own computed answer is shown instead.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.scenario import DATA_DIR


@dataclass(frozen=True)
class Capture:
    text: str | None
    status: str  # "captured" | "stale" | "missing"
    model: str | None


def captures_path() -> Path:
    return Path(os.environ.get("DEMO_CAPTURES_PATH", DATA_DIR / "captured_answers.json"))


def fingerprint(context_text: str) -> str:
    return hashlib.sha256(context_text.encode("utf-8")).hexdigest()[:16]


def load_captures() -> dict:
    path = captures_path()
    if not path.exists():
        return {"answers": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def find_capture(key: str, context_text: str) -> Capture:
    entry = load_captures()["answers"].get(key)
    if entry is None:
        return Capture(None, "missing", None)
    if entry["fingerprint"] != fingerprint(context_text):
        return Capture(None, "stale", entry.get("model"))
    return Capture(entry["answer_text"], "captured", entry.get("model"))


def save_capture(key: str, context_text: str, answer_text: str, model: str) -> None:
    data = load_captures()
    data["answers"][key] = {
        "fingerprint": fingerprint(context_text),
        "model": model,
        "captured_on": date.today().isoformat(),
        "answer_text": answer_text.strip(),
    }
    captures_path().write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
