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
from .tools import (
    ToolDefinition,
    ToolInvocation,
    ToolResult,
    build_function_tool,
    execute_tool,
    parse_tool_arguments,
)


def load_task(path: str | Path) -> HarnessTaskSpec:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_task_payload(raw)


def _render_tool_catalog(tools: list[ToolDefinition]) -> str:
    if not tools:
        return "[no tools configured]"
    lines = []
    for tool in tools:
        lines.append(f"- {tool.name}: {tool.description or 'no description'}")
    return "\n".join(lines)


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
    available_tools: str | None = None,
) -> str:
    template = default_task_prompt()
    prompt = template.format(
        task_name=task.name,
        user_prompt=task.user_prompt,
        metadata=json.dumps(task.metadata or {}, ensure_ascii=False, indent=2),
        shared_context=context_notes or "[no shared context]",
        tool_outputs=tool_notes or "[no tool outputs]",
        available_tools=available_tools or "[no available tools]",
    )
    return prompt


def _retry_delay(config: HarnessConfig, attempt: int) -> float:
    return config.retry_backoff_seconds * attempt


def _task_tool_definitions(task: HarnessTaskSpec) -> list[ToolDefinition]:
    tools: list[ToolDefinition] = []
    for tool in task.tools:
        tools.append(
            ToolDefinition(
                name=tool["name"],
                description=tool.get("description"),
                parameters=tool.get("parameters"),
                strict=bool(tool.get("strict", True)),
            )
        )
    return tools


def _call_tool(invocation: ToolInvocation, context: dict[str, Any]) -> ToolResult:
    return execute_tool(invocation, context=context)


def _extract_function_calls(response: Any) -> list[Any]:
    items = getattr(response, "output", []) or []
    return [item for item in items if getattr(item, "type", None) == "function_call"]


def _run_model(
    config: HarnessConfig,
    task: HarnessTaskSpec,
    context_notes: str | None = None,
    shared_context: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    if not config.api_key:
        return "未检测到 OPENAI_API_KEY，无法运行模型。", []

    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    system_prompt = task.system_prompt or default_system_prompt()
    tool_definitions = _task_tool_definitions(task)
    available_tools = [build_function_tool(tool) for tool in tool_definitions]
    user_prompt = render_task_prompt(
        task,
        context_notes=context_notes,
        available_tools=_render_tool_catalog(tool_definitions),
    )

    last_error: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            response = client.responses.create(
                model=config.model,
                instructions=system_prompt,
                input=[{"role": "user", "content": user_prompt}],
                tools=available_tools,
                parallel_tool_calls=True,
                temperature=task.temperature,
            )

            tool_trace: list[dict[str, Any]] = []
            for _ in range(config.max_tool_rounds):
                function_calls = _extract_function_calls(response)
                if not function_calls:
                    return getattr(response, "output_text", "").strip() or str(response), tool_trace

                tool_outputs = []
                for call in function_calls:
                    arguments = parse_tool_arguments(getattr(call, "arguments", "{}"), getattr(call, "name", ""))
                    invocation = ToolInvocation(
                        name=getattr(call, "name", ""),
                        arguments=arguments,
                        call_id=getattr(call, "call_id", ""),
                        model_call_id=getattr(call, "id", None),
                    )
                    result = _call_tool(invocation, context=shared_context or {})
                    tool_trace.append(
                        {
                            "name": invocation.name,
                            "call_id": invocation.call_id,
                            "model_call_id": invocation.model_call_id,
                            "arguments": invocation.arguments,
                            "output": result.output,
                            "ok": result.ok,
                            "error": result.error,
                        }
                    )
                    tool_outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": invocation.call_id,
                            "output": result.output if result.ok else json.dumps({"error": result.error}, ensure_ascii=False),
                        }
                    )

                response = client.responses.create(
                    model=config.model,
                    instructions=system_prompt,
                    previous_response_id=response.id,
                    input=tool_outputs,
                    tools=available_tools,
                    parallel_tool_calls=True,
                    temperature=task.temperature,
                )

            return getattr(response, "output_text", "").strip() or str(response), tool_trace
        except Exception as e:
            last_error = e
            if attempt >= config.max_retries:
                break
            import time

            time.sleep(_retry_delay(config, attempt + 1))
    return f"模型调用失败：{last_error}", []


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
    output, tool_trace = _run_model(
        config,
        task,
        context_notes=context_notes,
        shared_context=shared_context,
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
        "user_prompt": render_task_prompt(
            task,
            context_notes=context_notes,
            available_tools=_render_tool_catalog(_task_tool_definitions(task)),
        ),
        "tool_results": tool_trace,
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
