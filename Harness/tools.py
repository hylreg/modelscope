from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
import json


ToolFn = Callable[[dict[str, Any], dict[str, Any]], str]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None
    strict: bool = True


@dataclass(frozen=True)
class ToolInvocation:
    name: str
    arguments: dict[str, Any]
    call_id: str
    model_call_id: str | None = None


@dataclass(frozen=True)
class ToolResult:
    name: str
    output: str
    ok: bool = True
    error: str | None = None


_TOOL_REGISTRY: dict[str, ToolFn] = {}


def register_tool(name: str, fn: ToolFn) -> None:
    _TOOL_REGISTRY[name] = fn


def list_tools() -> list[str]:
    return sorted(_TOOL_REGISTRY)


def execute_tool(invocation: ToolInvocation, context: dict[str, Any] | None = None) -> ToolResult:
    context = context or {}
    fn = _TOOL_REGISTRY.get(invocation.name)
    if fn is None:
        return ToolResult(name=invocation.name, output="", ok=False, error=f"unknown tool: {invocation.name}")
    try:
        return ToolResult(name=invocation.name, output=fn(invocation.arguments, context), ok=True)
    except Exception as e:
        return ToolResult(name=invocation.name, output="", ok=False, error=str(e))


def build_function_tool(definition: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "name": definition.name,
        "description": definition.description,
        "parameters": definition.parameters or {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": definition.strict,
    }


def parse_tool_arguments(raw: str, tool_name: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"tool `{tool_name}` arguments are not valid JSON: {e}") from e
    if not isinstance(value, dict):
        raise ValueError(f"tool `{tool_name}` arguments must be a JSON object")
    return value


def _tool_echo(args: dict[str, Any], _context: dict[str, Any]) -> str:
    return str(args.get("text", ""))


def _tool_now_utc(_args: dict[str, Any], _context: dict[str, Any]) -> str:
    return datetime.now(timezone.utc).isoformat()


def _tool_json_pretty(args: dict[str, Any], _context: dict[str, Any]) -> str:
    value = args.get("value")
    return json.dumps(value, ensure_ascii=False, indent=2)


def _tool_context_summary(_args: dict[str, Any], context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, indent=2)


register_tool("echo", _tool_echo)
register_tool("now_utc", _tool_now_utc)
register_tool("json_pretty", _tool_json_pretty)
register_tool("context_summary", _tool_context_summary)
