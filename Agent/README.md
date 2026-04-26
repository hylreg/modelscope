# Minimal Skill Agent

一个很小的意图路由 agent，用来在 `Skills/*/SKILL.md` 之间选一个最合适的 skill。

## 工作流程

1. 扫描 `../Skills/*/SKILL.md`
2. 读取每个 skill 的 `name`、`description`、frontmatter 内容和引号里的触发词
3. 先用规则打分路由
4. 如果分数太低，或者第一名和第二名差距太小，再让 LLM 兜底选一个 skill
5. 把用户输入交给选中的 skill 执行

## 路由规则

`min_agent.py` 里的规则路由会综合下面几项：

- skill 的引号触发词命中，单项加权最高
- skill 名称是否直接出现在 query 里
- query 与 skill description 的词交集
- 一组中文关键词的交集

触发 LLM 兜底的条件是：

- 最高分 `< 5`
- 或者第一名和第二名的分差 `<= 2`

## 运行

```bash
uv run python Agent/min_agent.py "帮我根据JD润色简历"
```

只看路由结果，不执行 skill：

```bash
uv run python Agent/min_agent.py "帮我写一段面试自我介绍" --dry-run
```

## 环境变量

- `OPENAI_API_KEY`
- `OPENAI_MODEL`，默认 `gpt-4.1-mini`
- `OPENAI_BASE_URL`

## 参数

- `--skills-dir`：skills 目录，默认 `../Skills`
- `--model`：LLM 路由和执行使用的模型
- `--dry-run`：只路由，不执行 skill

## 说明

- 运行时会先打印本次路由是由 `规则` 还是 `LLM` 选出的 skill
- 如果没有配置 `OPENAI_API_KEY`，LLM 兜底会跳过
- 如果最终执行阶段没有可用模型，会输出 `模型不可用`
- `SKILL.md` 里只要有 frontmatter 的 `name` 和 `description`，再加上正文里用引号写的短语，就能参与路由

# Minimal MCP Agent

一个更小的 agent，用来直接连接本仓库里的最小 MCP Server，并调用其中暴露的工具。

## 运行

列出远端工具：

```bash
uv run python Agent/mcp_agent.py --list-tools
```

调用默认的 `echo` 工具：

```bash
uv run python Agent/mcp_agent.py --tool echo --arguments '{"text":"hello"}'
```

调用其他工具时，只要把 `--tool` 和 `--arguments` 换成对应的名字和 JSON 参数即可。
