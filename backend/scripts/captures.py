"""Manage the captured AI answers in data/captured_answers.json.

  python scripts/captures.py status                  # which captures match the current data
  python scripts/captures.py export                  # write each stage's exact prompt + context to data/contexts/
  python scripts/captures.py save 3 answer.txt       # store an AI answer for stage 3 (key: 1, 2, 3, 4:most_rows, 4:newest_dates)

To re-capture after editing scenario.json: export, give data/contexts/<key>.txt to an AI model,
save its answer to a file, then `save` it.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.captures import find_capture, fingerprint, save_capture  # noqa: E402
from app.engine import stage_context  # noqa: E402
from app.scenario import DATA_DIR  # noqa: E402

KEYS = {"1": (1, None), "2": (2, None), "3": (3, None), "4:most_rows": (4, "most_rows"), "4:newest_dates": (4, "newest_dates")}


def context_text(key: str) -> str:
    stage, trap = KEYS[key]
    return stage_context(stage, trap).full_text()


def cmd_status() -> None:
    for key in KEYS:
        print(f"  {key:<15} {find_capture(key, context_text(key)).status}")


def cmd_export() -> None:
    out = DATA_DIR / "contexts"
    out.mkdir(exist_ok=True)
    for key in KEYS:
        text = context_text(key)
        path = out / f"stage-{key.replace(':', '-')}.txt"
        path.write_text(text, encoding="utf-8")
        print(f"  {key:<15} {len(text):>8,} chars  fingerprint {fingerprint(text)}  -> {path.name}")


def cmd_save(key: str, answer_file: str, model: str) -> None:
    save_capture(key, context_text(key), Path(answer_file).read_text(encoding="utf-8"), model)
    print(f"Saved capture for {key}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("export")
    save = sub.add_parser("save")
    save.add_argument("key", choices=list(KEYS))
    save.add_argument("answer_file")
    save.add_argument("--model", default="claude-opus-5-5")
    args = parser.parse_args()

    if args.cmd == "status":
        cmd_status()
    elif args.cmd == "export":
        cmd_export()
    else:
        cmd_save(args.key, args.answer_file, args.model)


if __name__ == "__main__":
    main()
