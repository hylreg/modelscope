# LangGraph Examples

LangGraph 是一个用于构建状态化、多智能体应用的框架。本目录包含了一些示例，帮助您快速入门 LangGraph 的使用。

## 文件说明

### hello_world.py

一个最小的 `langgraph` 示例，对应下面这个流程：

1. 定义一个 `mock_llm` 节点
2. 从 `START` 连接到这个节点
3. 再从节点连接到 `END`
4. `invoke` 一次输入消息，返回 `hello world`

### quickstart.py

一个更全面的 LangGraph 快速入门示例，展示了如何使用工具、状态管理和图构建的基本概念。

## 运行示例

### 运行 hello_world.py

```bash
uv run python LangGraph/hello_world.py
```

### 运行 quickstart.py

```bash
uv run python LangGraph/quickstart.py
```

## 依赖项

这些示例需要以下依赖项：

- langgraph
- langchain
- ipython

如需安装依赖，请确保您已安装 `uv`，然后运行：

```bash
uv sync
```
