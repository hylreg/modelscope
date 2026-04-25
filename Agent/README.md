# Minimal Skill Agent

一个很小的意图路由 agent：

1. 扫描 `../Skills/*/SKILL.md`
2. 先用规则匹配 skill
3. 规则不确定时，用 LLM 选一个 skill
4. 把用户输入交给选中的 skill 执行

## 运行

```bash
uv run python Agent/min_agent.py "帮我根据JD润色简历"
```

只看路由结果：

```bash
uv run python Agent/min_agent.py "帮我写一段面试自我介绍" --dry-run
```

## 环境变量

- `OPENAI_API_KEY`
- `OPENAI_MODEL`，默认 `gpt-4.1-mini`
- `OPENAI_BASE_URL`

## 参数

- `--skills-dir`：skills 目录，默认 `../Skills`
- `--dry-run`：只路由，不执行 skill
