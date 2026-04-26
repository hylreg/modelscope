# LangGraph Hello World

一个最小的 `langgraph` 示例，对应下面这个流程：

1. 定义一个 `mock_llm` 节点
2. 从 `START` 连接到这个节点
3. 再从节点连接到 `END`
4. `invoke` 一次输入消息，返回 `hello world`

## 运行

```bash
uv run python LangGraph/hello_world.py
```

## 示例代码

```python
from langgraph.graph import StateGraph, MessagesState, START, END

def mock_llm(state: MessagesState):
    return {"messages": [{"role": "ai", "content": "hello world"}]}

graph = StateGraph(MessagesState)
graph.add_node(mock_llm)
graph.add_edge(START, "mock_llm")
graph.add_edge("mock_llm", END)
graph = graph.compile()

graph.invoke({"messages": [{"role": "user", "content": "hi!"}]})
```
