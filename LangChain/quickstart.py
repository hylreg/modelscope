import urllib.error
import urllib.request

from langchain.agents import create_agent
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

SYSTEM_PROMPT = """你是一个文学数据分析助手。

## 功能

- `fetch_text_from_url`: 从URL加载文档文本到对话中。
不要猜测行数或位置——以工具结果中的保存文件为准。"""


@tool
def fetch_text_from_url(url: str) -> str:
    """从URL获取文档。
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; quickstart-research/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        return f"获取失败: {e}"
    text = raw.decode("utf-8", errors="replace")
    return text


model = init_chat_model(
    "qwen3.5-flash",
    model_provider="openai",
    temperature=0.5,
    timeout=600,
    max_tokens=25000,
    streaming=True,
)

checkpointer = InMemorySaver()

agent = create_agent(
    model=model,
    tools=[fetch_text_from_url],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

deep_agent = create_deep_agent(
    model=model,
    tools=[fetch_text_from_url],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)

content = f"""古腾堡计划托管了F·斯科特·菲茨杰拉德的《了不起的盖茨比》完整纯文本。
URL: https://www.gutenberg.org/files/64317/64317-0.txt

请尽可能多地回答以下问题:

1) 在完整的古腾堡文件中，有多少行包含子串 `Gatsby`（计算行数，而不是一行内的出现次数，每行以换行符结尾）。
2) 包含 `Daisy` 的第一行的1索引行号。
3) 一个两句的中立概要。

对(1)和(2)尽最大努力。如果你在任何时候意识到你无法用可用工具和推理来**验证**确切答案，
请不要编造数字：对该字段使用 `null` 并在 `how_you_computed_counts` 中说明限制。
如果遇到任何错误，请报告错误内容和错误消息。"""

agent_result = agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "great-gatsby-lc"}},
)
deep_agent_result = deep_agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "great-gatsby-da"}},
)
print(agent_result["messages"][-1].content_blocks)
print("\n")
print(deep_agent_result["messages"][-1].content_blocks)