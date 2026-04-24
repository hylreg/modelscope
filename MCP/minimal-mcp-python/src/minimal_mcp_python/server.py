from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("minimal-mcp-python")


@mcp.tool()
def echo(text: str) -> str:
    return text


def main() -> None:
    print("minimal-mcp-python MCP server running (stdio). Waiting for a client...", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()

