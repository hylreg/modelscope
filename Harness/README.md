# Hermes Engineering Harness Template

这是一个面向 `Hermes Engineering` 的最小框架模板，用来快速搭建：

- 统一的任务入口
- 可配置的系统提示词
- 可复用的运行器
- 示例任务定义

设计目标是先把工程骨架搭起来，再按你的业务流程逐步扩展。

## 目录结构

```text
Harness/
  README.md
  cli.py
  config.py
  prompts.py
  runner.py
  examples/
    sample_task.json
  templates/
    system_prompt.md
    task_prompt.md
```

## 运行方式

```bash
python -m Harness.cli --task Harness/examples/sample_task.json
```

只预览配置，不调用模型：

```bash
python -m Harness.cli --task Harness/examples/sample_task.json --dry-run
```

## 环境变量

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`，可选
- `OPENAI_MODEL`，默认 `gpt-4.1-mini`

## 你可以扩展的点

- 把 `examples/sample_task.json` 改成你的任务协议
- 在 `templates/system_prompt.md` 中写 Hermes Engineering 的固定系统规则
- 在 `runner.py` 中接入评分、工具调用、重试、日志落盘
- 在 `cli.py` 中增加批处理、目录扫描、并发执行

