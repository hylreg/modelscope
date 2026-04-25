from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TaskSchemaError(ValueError):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class TaskCheck:
    kind: str
    value: str


@dataclass(frozen=True)
class HarnessTaskSpec:
    name: str
    user_prompt: str
    system_prompt: str | None = None
    temperature: float = 0.2
    metadata: dict[str, Any] = field(default_factory=dict)
    checks: list[TaskCheck] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowStepSpec:
    task: str
    label: str | None = None
    include_previous_output: bool = True


@dataclass(frozen=True)
class HarnessWorkflowSpec:
    name: str
    steps: list[WorkflowStepSpec]
    metadata: dict[str, Any] = field(default_factory=dict)


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TaskSchemaError(f"field `{key}` must be a non-empty string")
    return value.strip()


def _optional_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TaskSchemaError(f"field `{key}` must be a string if present")
    value = value.strip()
    return value or None


def _optional_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TaskSchemaError(f"field `{key}` must be an object if present")
    return value


def _optional_checks(payload: dict[str, Any]) -> list[TaskCheck]:
    raw_checks = payload.get("checks")
    if raw_checks is None:
        return []
    if not isinstance(raw_checks, list):
        raise TaskSchemaError("field `checks` must be an array if present")

    checks: list[TaskCheck] = []
    for index, item in enumerate(raw_checks):
        if not isinstance(item, dict):
            raise TaskSchemaError(f"checks[{index}] must be an object")
        kind = _require_str(item, "kind")
        value = _require_str(item, "value")
        if kind not in {"contains", "equals", "startswith", "endswith"}:
            raise TaskSchemaError(
                f"checks[{index}].kind must be one of contains, equals, startswith, endswith"
            )
        checks.append(TaskCheck(kind=kind, value=value))
    return checks


def _optional_steps(payload: dict[str, Any]) -> list[WorkflowStepSpec]:
    raw_steps = payload.get("steps")
    if raw_steps is None:
        return []
    if not isinstance(raw_steps, list):
        raise TaskSchemaError("field `steps` must be an array if present")

    steps: list[WorkflowStepSpec] = []
    for index, item in enumerate(raw_steps):
        if not isinstance(item, dict):
            raise TaskSchemaError(f"steps[{index}] must be an object")
        task = _require_str(item, "task")
        label = _optional_str(item, "label")
        include_previous_output = item.get("include_previous_output", True)
        if not isinstance(include_previous_output, bool):
            raise TaskSchemaError(
                f"steps[{index}].include_previous_output must be a boolean if present"
            )
        steps.append(
            WorkflowStepSpec(
                task=task,
                label=label,
                include_previous_output=include_previous_output,
            )
        )
    return steps


def validate_task_payload(payload: dict[str, Any]) -> HarnessTaskSpec:
    if not isinstance(payload, dict):
        raise TaskSchemaError("task payload must be a JSON object")

    name = _require_str(payload, "name") if payload.get("name") is not None else "unnamed-task"
    user_prompt = _require_str(payload, "user_prompt")
    system_prompt = _optional_str(payload, "system_prompt")
    metadata = _optional_dict(payload, "metadata")
    checks = _optional_checks(payload)

    try:
        temperature = float(payload.get("temperature", 0.2))
    except (TypeError, ValueError) as e:
        raise TaskSchemaError("field `temperature` must be a number") from e
    if temperature < 0 or temperature > 2:
        raise TaskSchemaError("field `temperature` must be between 0 and 2")

    return HarnessTaskSpec(
        name=name,
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        metadata=metadata,
        checks=checks,
    )


def validate_workflow_payload(payload: dict[str, Any]) -> HarnessWorkflowSpec:
    if not isinstance(payload, dict):
        raise TaskSchemaError("workflow payload must be a JSON object")

    name = _require_str(payload, "name") if payload.get("name") is not None else "unnamed-workflow"
    metadata = _optional_dict(payload, "metadata")
    steps = _optional_steps(payload)
    if not steps:
        raise TaskSchemaError("workflow must contain at least one step")

    return HarnessWorkflowSpec(name=name, steps=steps, metadata=metadata)
