from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .runner import load_task, run_task
from .schema import TaskSchemaError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hermes Engineering harness template")
    parser.add_argument("--task", required=True, help="JSON task file")
    parser.add_argument("--dry-run", action="store_true", help="Only print task and exit")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        task = load_task(Path(args.task))
    except (OSError, json.JSONDecodeError, TaskSchemaError) as e:
        raise SystemExit(f"task load failed: {e}")

    if args.dry_run:
        print(f"[dry-run] task={task.name}")
        print(task)
        return

    config = load_config()
    result = run_task(config, task)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["output"])
        if result["evaluation"]["total"]:
            print(
                f"[eval] {result['evaluation']['passed_checks']}/{result['evaluation']['total']} passed"
            )
        print(f"[run] saved to {result['run_file']}")


if __name__ == "__main__":
    main()
