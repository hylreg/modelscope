from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .runner import load_task, run_task


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hermes Engineering harness template")
    parser.add_argument("--task", required=True, help="JSON task file")
    parser.add_argument("--dry-run", action="store_true", help="Only print task and exit")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    task = load_task(Path(args.task))

    if args.dry_run:
        print(f"[dry-run] task={task.name}")
        print(task)
        return

    config = load_config()
    print(run_task(config, task))


if __name__ == "__main__":
    main()

