# Minimal Skill Agent

一个最小可运行的意图路由 Agent：

1. 自动加载 `../Skills/*/SKILL.md`
2. 根据用户输入做意图匹配，选中最合适的 skill
3. 自动调用 skill（若配置了 `OPENAI_API_KEY`）

## 运行

```bash
uv run python Agent/min_agent.py "帮我根据JD润色简历"
```

只看路由结果（不调用模型）：

```bash
uv run python Agent/min_agent.py "帮我写一段面试自我介绍" --dry-run
```

## 可选环境变量

- `OPENAI_API_KEY`：配置后会自动调用模型
- `OPENAI_MODEL`：默认 `gpt-4.1-mini`
- `OPENAI_BASE_URL`：可选，兼容 OpenAI-compatible 网关

## 参数

- `--skills-dir`：自定义 skills 目录（默认 `../Skills`）
- `--dry-run`：仅路由，不调用模型
