#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


SERVER_CWD = Path(__file__).resolve().parents[1] / "MCP/minimal-mcp-python"
SERVER_COMMAND = "uv"
SERVER_ARGS = ["run", "python", "-m", "minimal_mcp_python.server"]
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Use an LLM to pick an MCP tool and call it.")
    parser.add_argument("request", nargs="?", default="", help="自然语言请求")
    parser.add_argument("--list-tools", action="store_true", help="只列出工具名")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM 模型名")
    return parser


def build_server_params() -> StdioServerParameters:
    """描述如何启动本地 MCP server。"""
    return StdioServerParameters(
        command=SERVER_COMMAND,
        args=SERVER_ARGS,
        cwd=SERVER_CWD,
    )


def tools_to_prompt(tools: list[Any]) -> str:
    """把 MCP 工具列表整理成一段给 LLM 看的文本。"""
    lines: list[str] = []
    for tool in tools:
        lines.append(
            json.dumps(
                {
                    "name": getattr(tool, "name", ""),
                    "description": getattr(tool, "description", ""),
                    "inputSchema": getattr(tool, "inputSchema", {}),
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines)


def parse_llm_choice(text: str) -> tuple[str, dict[str, Any]]:
    """把 LLM 的返回解析成 tool name + arguments。"""
    text = text.strip()
    if not text:
        raise ValueError("LLM 没有返回内容")

    if text.startswith("```"):
        text = text.strip("`").strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < 0 or end <= start:
            raise
        data = json.loads(text[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("LLM 返回的内容不是 JSON object")

    tool_name = str(data.get("tool", "")).strip()
    if not tool_name or tool_name.upper() == "NONE":
        raise ValueError("LLM 没有选择任何工具")

    arguments = data.get("arguments") or {}
    if not isinstance(arguments, dict):
        raise ValueError("LLM 返回的 arguments 不是 JSON object")

    return tool_name, arguments


def choose_tool_with_llm(request: str, tools: list[Any], model: str) -> tuple[str, dict[str, Any]]:
    """让 LLM 在工具列表里选一个工具，并生成该工具的参数。"""
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("没有可用的 OpenAI 配置，无法自动选择工具")

    kwargs: dict[str, Any] = {}
    if base_url := os.getenv("OPENAI_BASE_URL"):
        kwargs["base_url"] = base_url

    client = OpenAI(**kwargs)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": "Choose exactly one MCP tool and return JSON only.",
            },
            {
                "role": "user",
                "content": (
                    "Available tools:\n"
                    f"{tools_to_prompt(tools)}\n\n"
                    "User request:\n"
                    f"{request}\n\n"
                    'Return JSON with keys "tool" and "arguments". '
                    'If nothing fits, use {"tool":"NONE","arguments":{}}.'
                ),
            },
        ],
    )

    output_text = getattr(response, "output_text", "")
    return parse_llm_choice(output_text)


def render_result(result: Any) -> str:
    """把 MCP 返回值转成适合打印的文本。"""
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False)

    content = getattr(result, "content", None) or []
    lines: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text":
            lines.append(getattr(block, "text", ""))
        elif hasattr(block, "model_dump"):
            lines.append(json.dumps(block.model_dump(), ensure_ascii=False))
        elif isinstance(block, dict):
            lines.append(json.dumps(block, ensure_ascii=False))
        else:
            lines.append(str(block))
    return "\n".join(lines) if lines else str(result)


async def run(args: argparse.Namespace) -> int:
    """主流程：
    1. 启动本地 MCP server
    2. 连接 server
    3. 读取工具列表
    4. 要么列出工具，要么交给 LLM 选工具并调用
    """
    async with stdio_client(build_server_params()) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            if args.list_tools:
                for tool in tools.tools:
                    print(tool.name)
                return 0

            if not args.request.strip():
                raise ValueError("自动选工具时必须提供 request")

            tool_name, tool_arguments = choose_tool_with_llm(args.request, tools.tools, args.model)
            print(f"[route] LLM chose tool: {tool_name}")

            result = await session.call_tool(tool_name, arguments=tool_arguments)
            print(render_result(result))
            return 0


def main() -> None:
    args = build_parser().parse_args()
    try:
        raise SystemExit(asyncio.run(run(args)))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"参数解析失败：{exc}") from exc
    except Exception as exc:
        raise SystemExit(f"调用 MCP 失败：{exc}") from exc


if __name__ == "__main__":
    main()
