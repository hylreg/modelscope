from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .logging_utils import save_run_record
from .runner import load_task, run_task
from .schema import TaskSchemaError
from .workflow import load_workflow, run_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hermes Engineering harness template")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", help="JSON task file")
    group.add_argument("--tasks-dir", help="Directory of task JSON files")
    group.add_argument("--workflow", help="Workflow JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Only print task and exit")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output")
    parser.add_argument("--pattern", default="*.json", help="File glob for --tasks-dir")
    return parser


def _run_single_task(args: argparse.Namespace) -> dict:
    try:
        task = load_task(Path(args.task))
    except (OSError, json.JSONDecodeError, TaskSchemaError) as e:
        raise SystemExit(f"task load failed: {e}")

    if args.dry_run:
        print(f"[dry-run] task={task.name}")
        print(task)
        raise SystemExit(0)

    config = load_config()
    return run_task(config, task)


def _run_task_dir(args: argparse.Namespace) -> dict:
    config = load_config()
    root = Path(args.tasks_dir)
    results: list[dict] = []
    for path in sorted(root.glob(args.pattern)):
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            results.append(
                {
                    "task_file": str(path.resolve()),
                    "status": "error",
                    "error": str(e),
                }
            )
            continue
        if isinstance(raw, dict) and "steps" in raw:
            results.append(
                {
                    "task_file": str(path.resolve()),
                    "status": "skipped",
                    "reason": "workflow file",
                }
            )
            continue
        try:
            task = load_task(path)
            if args.dry_run:
                print(f"[dry-run] task={task.name} <- {path}")
                print(task)
                continue
            results.append(run_task(config, task))
        except (OSError, json.JSONDecodeError, TaskSchemaError) as e:
            results.append(
                {
                    "task_file": str(path.resolve()),
                    "status": "error",
                    "error": str(e),
                }
            )

    summary = {
        "mode": "batch",
        "tasks_dir": str(root.resolve()),
        "pattern": args.pattern,
        "total": len(results),
        "passed": sum(1 for item in results if item.get("evaluation", {}).get("passed")),
        "failed": sum(
            1
            for item in results
            if item.get("status") == "error"
            or (item.get("evaluation") is not None and not item.get("evaluation", {}).get("passed"))
        ),
        "skipped": sum(1 for item in results if item.get("status") == "skipped"),
    }
    record = {
        "task_name": f"batch-{root.name}",
        "mode": "batch",
        "summary": summary,
        "items": results,
    }
    record["run_file"] = str(save_run_record(config.runs_dir, record))
    return {"summary": summary, "items": results, "run_file": record["run_file"]}


def main() -> None:
    args = build_parser().parse_args()
    if args.workflow:
        if args.dry_run:
            try:
                workflow = load_workflow(Path(args.workflow))
            except (OSError, json.JSONDecodeError, TaskSchemaError) as e:
                raise SystemExit(f"workflow load failed: {e}")
            print(f"[dry-run] workflow={workflow.name}")
            print(workflow)
            return
        result = run_workflow(load_config(), args.workflow)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
            for step in result["steps"]:
                status = step["status"]
                print(f"[step {step['step_index']}] {step['step_name']} -> {status}")
                if step.get("run_file"):
                    print(f"  run: {step['run_file']}")
                if step.get("error"):
                    print(f"  error: {step['error']}")
            print(f"[run] saved to {result['run_file']}")
        return

    if args.tasks_dir:
        result = _run_task_dir(args)
        if args.dry_run:
            return
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
            for item in result["items"]:
                if item.get("status") == "error":
                    print(f"[error] {item['task_file']}: {item['error']}")
                elif item.get("status") == "skipped":
                    print(f"[skip] {item['task_file']}: {item['reason']}")
                else:
                    print(f"[task] {item['task_name']} -> {item['run_file']}")
            print(f"[run] saved to {result['run_file']}")
        return

    result = _run_single_task(args)
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
