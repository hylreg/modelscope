#!/usr/bin/env python3
from __future__ import annotations

"""A tiny MCP client that talks to the local demo server over stdio."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
# 这个脚本默认只连仓库里的最小 MCP Server。
SERVER_CWD = Path(__file__).resolve().parents[1] / "MCP/minimal-mcp-python"
SERVER_COMMAND = "uv"
SERVER_ARGS = ["run", "python", "-m", "minimal_mcp_python.server"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Connect to the local MCP server and call one tool.")
    parser.add_argument(
        "--tool",
        default="echo",
        help="要调用的工具名，默认 echo",
    )
    parser.add_argument(
        "--arguments",
        default="{}",
        help="传给工具的 JSON 参数，例如 '{\"text\":\"hello\"}'",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="只列出工具名，不调用工具",
    )
    return parser


def parse_arguments(raw: str) -> dict[str, Any]:
    """把命令行里的 JSON 字符串转成 MCP 需要的 dict。"""
    if not raw.strip():
        return {}

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("--arguments 必须是 JSON object")
    return data


def format_result(result: Any) -> str:
    """把 MCP 的返回值整理成可直接打印的文本。"""
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False)

    content = getattr(result, "content", None)
    if not content:
        return str(result)

    parts: list[str] = []
    for block in content:
        # MCP 的 content 通常是一个个 block，这里尽量把它们变成人类可读文本。
        block_type = getattr(block, "type", None)
        if block_type == "text":
            parts.append(getattr(block, "text", ""))
        elif hasattr(block, "model_dump"):
            parts.append(json.dumps(block.model_dump(), ensure_ascii=False))
        elif isinstance(block, dict):
            parts.append(json.dumps(block, ensure_ascii=False))
        else:
            parts.append(str(block))
    return "\n".join(parts)


async def run(args: argparse.Namespace) -> int:
    """启动本地 server，连接进去，然后列工具或调用工具。"""
    tool_arguments = parse_arguments(args.arguments)

    # 1. 先告诉 MCP client：要启动哪个命令、在哪个目录启动。
    server_params = StdioServerParameters(
        command=SERVER_COMMAND,
        args=SERVER_ARGS,
        cwd=SERVER_CWD,
    )

    # 2. stdio_client 会启动子进程，并把它的 stdin/stdout 包成流。
    async with stdio_client(server_params) as (read_stream, write_stream):
        # 3. ClientSession 负责按 MCP 协议和 server 对话。
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # 先取工具列表。这样即使后面不调用，也能看到 server 暴露了什么。
            tools = await session.list_tools()
            if args.list_tools:
                for tool in tools.tools:
                    print(tool.name)
                return 0

            # 不列工具的话，就直接调用指定工具。
            result = await session.call_tool(args.tool, arguments=tool_arguments)
            print(format_result(result))
            return 0


def main() -> None:
    """命令行入口。"""
    args = build_parser().parse_args()
    try:
        raise SystemExit(asyncio.run(run(args)))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"参数解析失败：{exc}") from exc
    except Exception as exc:
        raise SystemExit(f"调用 MCP 失败：{exc}") from exc


if __name__ == "__main__":
    main()
