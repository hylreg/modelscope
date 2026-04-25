from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_run_dir(base_dir: str | Path) -> Path:
    path = Path(base_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_run_record(base_dir: str | Path, record: dict[str, Any]) -> Path:
    run_dir = ensure_run_dir(base_dir)
    filename = f"run-{timestamp_slug()}-{record.get('task_name', 'task')}.json"
    target = run_dir / filename
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return target.resolve()
