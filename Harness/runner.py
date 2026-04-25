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
from .tools import ToolResult, ToolSpec, execute_tool


def load_task(path: str | Path) -> HarnessTaskSpec:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_task_payload(raw)


def _render_tool_section(tool_results: list[ToolResult]) -> str:
    if not tool_results:
        return ""
    lines = []
    for item in tool_results:
        status = "ok" if item.ok else f"error: {item.error}"
        lines.append(f"- {item.name}: {status}")
        if item.output:
            lines.append(item.output)
    return "\n".join(lines)


def render_task_prompt(
    task: HarnessTaskSpec,
    context_notes: str | None = None,
    tool_notes: str | None = None,
) -> str:
    template = default_task_prompt()
    prompt = template.format(
        task_name=task.name,
        user_prompt=task.user_prompt,
        metadata=json.dumps(task.metadata or {}, ensure_ascii=False, indent=2),
        shared_context=context_notes or "[no shared context]",
        tool_outputs=tool_notes or "[no tool outputs]",
    )
    return prompt


def _retry_delay(config: HarnessConfig, attempt: int) -> float:
    return config.retry_backoff_seconds * attempt


def _run_model(
    config: HarnessConfig,
    task: HarnessTaskSpec,
    context_notes: str | None = None,
    tool_results: list[ToolResult] | None = None,
) -> str:
    if not config.api_key:
        return "未检测到 OPENAI_API_KEY，无法运行模型。"

    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    system_prompt = task.system_prompt or default_system_prompt()
    user_prompt = render_task_prompt(
        task,
        context_notes=context_notes,
        tool_notes=_render_tool_section(tool_results or []),
    )

    last_error: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            response = client.responses.create(
                model=config.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=task.temperature,
            )
            return getattr(response, "output_text", "").strip() or str(response)
        except Exception as e:
            last_error = e
            if attempt >= config.max_retries:
                break
            import time

            time.sleep(_retry_delay(config, attempt + 1))
    return f"模型调用失败：{last_error}"


def _execute_task_tools(task: HarnessTaskSpec, context: dict[str, Any] | None = None) -> list[ToolResult]:
    results: list[ToolResult] = []
    for tool_item in task.tools:
        result = execute_tool(ToolSpec(name=tool_item["name"], args=tool_item.get("args", {})), context=context)
        results.append(result)
    return results


def run_task(config: HarnessConfig, task: HarnessTaskSpec) -> dict[str, Any]:
    return run_task_with_context(config, task)


def run_task_with_context(
    config: HarnessConfig,
    task: HarnessTaskSpec,
    context_notes: str | None = None,
    shared_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    shared_context = shared_context or {}
    tool_results = _execute_task_tools(task, context=shared_context)
    output = _run_model(
        config,
        task,
        context_notes=context_notes,
        tool_results=tool_results,
    )
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
        "tools": task.tools,
        "system_prompt": task.system_prompt or default_system_prompt(),
        "user_prompt": render_task_prompt(task, context_notes=context_notes, tool_notes=_render_tool_section(tool_results)),
        "tool_results": [result.__dict__ for result in tool_results],
        "shared_context": shared_context,
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
