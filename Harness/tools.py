from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


ToolFn = Callable[[dict[str, Any], dict[str, Any]], str]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    args: dict[str, Any]


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


def execute_tool(spec: ToolSpec, context: dict[str, Any] | None = None) -> ToolResult:
    context = context or {}
    fn = _TOOL_REGISTRY.get(spec.name)
    if fn is None:
        return ToolResult(name=spec.name, output="", ok=False, error=f"unknown tool: {spec.name}")
    try:
        return ToolResult(name=spec.name, output=fn(spec.args, context), ok=True)
    except Exception as e:
        return ToolResult(name=spec.name, output="", ok=False, error=str(e))


def _tool_echo(args: dict[str, Any], _context: dict[str, Any]) -> str:
    return str(args.get("text", ""))


def _tool_now_utc(_args: dict[str, Any], _context: dict[str, Any]) -> str:
    return datetime.now(timezone.utc).isoformat()


def _tool_json_pretty(args: dict[str, Any], _context: dict[str, Any]) -> str:
    import json

    value = args.get("value")
    return json.dumps(value, ensure_ascii=False, indent=2)


def _tool_context_summary(_args: dict[str, Any], context: dict[str, Any]) -> str:
    import json

    return json.dumps(context, ensure_ascii=False, indent=2)


register_tool("echo", _tool_echo)
register_tool("now_utc", _tool_now_utc)
register_tool("json_pretty", _tool_json_pretty)
register_tool("context_summary", _tool_context_summary)
