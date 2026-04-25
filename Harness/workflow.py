from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import HarnessConfig
from .logging_utils import save_run_record
from .prompts import default_workflow_prompt
from .runner import load_task, run_task_with_context
from .schema import HarnessWorkflowSpec, TaskSchemaError, validate_workflow_payload


@dataclass(frozen=True)
class WorkflowStepResult:
    step_index: int
    step_name: str
    task_path: str
    status: str
    output: str | None = None
    run_file: str | None = None
    error: str | None = None
    evaluation: dict[str, Any] | None = None


def load_workflow(path: str | Path) -> HarnessWorkflowSpec:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_workflow_payload(raw)


def render_workflow_context(
    workflow_name: str,
    step_index: int,
    step_total: int,
    previous_output: str | None,
) -> str:
    template = default_workflow_prompt()
    return template.format(
        workflow_name=workflow_name,
        step_index=step_index,
        step_total=step_total,
        previous_output=previous_output or "[no previous output]",
    )


def run_workflow(config: HarnessConfig, workflow_path: str | Path) -> dict[str, Any]:
    workflow_path = Path(workflow_path)
    workflow = load_workflow(workflow_path)

    results: list[WorkflowStepResult] = []
    previous_output: str | None = None
    base_dir = workflow_path.parent

    for index, step in enumerate(workflow.steps, start=1):
        step_path = (base_dir / step.task).resolve()
        step_name = step.label or step_path.stem
        try:
            task = load_task(step_path)
            context_notes = None
            if step.include_previous_output:
                context_notes = render_workflow_context(
                    workflow_name=workflow.name,
                    step_index=index,
                    step_total=len(workflow.steps),
                    previous_output=previous_output,
                )
            result = run_task_with_context(config, task, context_notes=context_notes)
            previous_output = result["output"]
            results.append(
                WorkflowStepResult(
                    step_index=index,
                    step_name=step_name,
                    task_path=str(step_path),
                    status="ok",
                    output=result["output"],
                    run_file=result["run_file"],
                    evaluation=result["evaluation"],
                )
            )
        except (OSError, json.JSONDecodeError, TaskSchemaError) as e:
            results.append(
                WorkflowStepResult(
                    step_index=index,
                    step_name=step_name,
                    task_path=str(step_path),
                    status="error",
                    error=str(e),
                )
            )
            break

    summary = {
        "workflow_name": workflow.name,
        "workflow_path": str(workflow_path.resolve()),
        "metadata": workflow.metadata,
        "steps_total": len(workflow.steps),
        "steps_completed": sum(1 for item in results if item.status == "ok"),
        "steps_errors": sum(1 for item in results if item.status == "error"),
        "checks_passed": sum(1 for item in results if item.evaluation and item.evaluation.get("passed")),
        "checks_failed": sum(
            1
            for item in results
            if item.status == "ok" and not (item.evaluation and item.evaluation.get("passed"))
        ),
    }
    record = {
        "task_name": workflow.name,
        "mode": "workflow",
        "summary": summary,
        "steps": [result.__dict__ for result in results],
    }
    record["run_file"] = str(save_run_record(config.runs_dir, record))
    return {
        "summary": summary,
        "steps": [result.__dict__ for result in results],
        "run_file": record["run_file"],
        "record": record,
    }
