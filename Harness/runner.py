from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from .config import HarnessConfig
from .eval import EvalResult, evaluate_task
from .logging_utils import save_run_record
from .prompts import default_system_prompt, default_task_prompt
from .schema import HarnessTaskSpec, validate_task_payload


def load_task(path: str | Path) -> HarnessTaskSpec:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_task_payload(raw)


def render_task_prompt(task: HarnessTaskSpec, context_notes: str | None = None) -> str:
    template = default_task_prompt()
    prompt = template.format(
        task_name=task.name,
        user_prompt=task.user_prompt,
        metadata=json.dumps(task.metadata or {}, ensure_ascii=False, indent=2),
    )
    if context_notes:
        prompt = f"{prompt}\n\n{context_notes.strip()}\n"
    return prompt


def _run_model(config: HarnessConfig, task: HarnessTaskSpec, context_notes: str | None = None) -> str:
    if not config.api_key:
        return "未检测到 OPENAI_API_KEY，无法运行模型。"

    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    system_prompt = task.system_prompt or default_system_prompt()
    user_prompt = render_task_prompt(task, context_notes=context_notes)

    response = client.responses.create(
        model=config.model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=task.temperature,
    )
    return getattr(response, "output_text", "").strip() or str(response)


def run_task(config: HarnessConfig, task: HarnessTaskSpec) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    output = _run_model(config, task)
    evaluation: EvalResult = evaluate_task(task, output)
    finished_at = datetime.now(timezone.utc).isoformat()

    record = {
        "task_name": task.name,
        "started_at": started_at,
        "finished_at": finished_at,
        "model": config.model,
        "base_url": config.base_url,
        "temperature": task.temperature,
        "metadata": task.metadata,
        "system_prompt": task.system_prompt or default_system_prompt(),
        "user_prompt": render_task_prompt(task),
        "output": output,
        "evaluation": {
            "passed": evaluation.passed,
            "total": evaluation.total,
            "passed_checks": evaluation.passed_checks,
            "failed_checks": evaluation.failed_checks,
        },
    }
    record["run_file"] = str(save_run_record(config.runs_dir, record))
    return record


def run_task_with_context(
    config: HarnessConfig,
    task: HarnessTaskSpec,
    context_notes: str | None = None,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    output = _run_model(config, task, context_notes=context_notes)
    evaluation: EvalResult = evaluate_task(task, output)
    finished_at = datetime.now(timezone.utc).isoformat()

    record = {
        "task_name": task.name,
        "started_at": started_at,
        "finished_at": finished_at,
        "model": config.model,
        "base_url": config.base_url,
        "temperature": task.temperature,
        "metadata": task.metadata,
        "system_prompt": task.system_prompt or default_system_prompt(),
        "user_prompt": render_task_prompt(task, context_notes=context_notes),
        "context_notes": context_notes,
        "output": output,
        "evaluation": {
            "passed": evaluation.passed,
            "total": evaluation.total,
            "passed_checks": evaluation.passed_checks,
            "failed_checks": evaluation.failed_checks,
        },
    }
    record["run_file"] = str(save_run_record(config.runs_dir, record))
    return record
