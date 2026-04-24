# minimal-mcp-python

一个**最小可运行**的 MCP Server 模板（Python + uv）。

## 目录结构

```
minimal-mcp-python/
  pyproject.toml
  README.md
  src/minimal_mcp_python/
    __init__.py
    server.py
```

## 运行

方式 A：先进入本模板目录再运行（推荐）：

```bash
cd MCP/minimal-mcp-python
uv run minimal-mcp-python
```

或：

```bash
cd MCP/minimal-mcp-python
uv run python -m minimal_mcp_python.server
```

方式 B：不切目录，显式指定项目路径：

```bash
uv --project MCP/minimal-mcp-python run minimal-mcp-python
```

或：

```bash
uv --project MCP/minimal-mcp-python run python -m minimal_mcp_python.server
```

## 给客户端的配置示例

本目录提供了一个 `mcp.json` 示例（不同客户端字段可能略有差异），核心就是用 `uv run` 作为启动命令。

## 包含内容

- `echo` 工具：输入什么返回什么（用于验证连通性）

