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


DEFAULT_SERVER_ARGS = [
    "run",
    "python",
    "-m",
    "minimal_mcp_python.server",
]
DEFAULT_SERVER_CWD = Path(__file__).resolve().parents[1] / "MCP/minimal-mcp-python"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tool",
        default="echo",
        help="要调用的 MCP 工具名，默认 echo",
    )
    parser.add_argument(
        "--arguments",
        default="{}",
        help="传给工具的 JSON 参数，例如 '{\"text\":\"hello\"}'",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="只列出远端 MCP server 暴露的工具",
    )
    parser.add_argument(
        "--server-command",
        default="uv",
        help="启动 MCP server 的命令，默认 uv",
    )
    parser.add_argument(
        "--server-cwd",
        default=str(DEFAULT_SERVER_CWD),
        help="启动 MCP server 时的工作目录，默认指向本仓库的 minimal server",
    )
    parser.add_argument(
        "--server-args",
        nargs=argparse.REMAINDER,
        default=DEFAULT_SERVER_ARGS,
        help="启动 MCP server 的参数；默认指向本仓库的 minimal server",
    )
    return parser


def _parse_arguments(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}

    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("`--arguments` 必须是 JSON object")
    return value


def _format_content_block(block: Any) -> str:
    block_type = getattr(block, "type", None)
    if block_type == "text":
        return getattr(block, "text", "")
    if hasattr(block, "model_dump"):
        return json.dumps(block.model_dump(), ensure_ascii=False)
    if isinstance(block, dict):
        return json.dumps(block, ensure_ascii=False)
    return str(block)


def _format_tool_result(result: Any) -> str:
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False)

    content = getattr(result, "content", None)
    if content:
        return "\n".join(_format_content_block(block) for block in content)

    return str(result)


def _server_env() -> dict[str, str]:
    # `uv` 会复用环境变量启动子进程；去掉当前虚拟环境标记，避免子项目提示环境不匹配。
    return {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}


async def run(args: argparse.Namespace) -> int:
    arguments = _parse_arguments(args.arguments)
    server_params = StdioServerParameters(
        command=args.server_command,
        args=args.server_args,
        env=_server_env(),
        cwd=args.server_cwd,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            if args.list_tools:
                for tool in tools.tools:
                    print(tool.name)
                return 0

            result = await session.call_tool(args.tool, arguments=arguments)
            print(_format_tool_result(result))
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
