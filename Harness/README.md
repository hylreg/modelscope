# Hermes Engineering Harness Template

这是一个面向 `Hermes Engineering` 的可扩展框架模板，用来快速搭建：

- 统一的任务入口
- 可配置的系统提示词
- 可复用的运行器
- 示例任务定义
- 输入校验
- 结果评估
- 运行日志落盘
- 批处理目录执行
- 多步工作流执行
- 本地工具调用接口
- 工作流共享上下文
- 批处理并发

设计目标是先把工程骨架搭起来，再按你的业务流程逐步扩展。

## 目录结构

```text
Harness/
  README.md
  cli.py
  config.py
  eval.py
  logging_utils.py
  prompts.py
  runner.py
  schema.py
  workflow.py
  tools.py
  examples/
    sample_task.json
    tool_task.json
    workflow_sample.json
    workflow_step_01.json
    workflow_step_02.json
  templates/
    system_prompt.md
    task_prompt.md
    workflow_prompt.md
```

## 运行方式

```bash
python -m Harness.cli --task Harness/examples/sample_task.json
```

只预览配置，不调用模型：

```bash
python -m Harness.cli --task Harness/examples/sample_task.json --dry-run
```

输出结构化结果：

```bash
python -m Harness.cli --task Harness/examples/sample_task.json --json
```

批量执行一个目录下的任务：

```bash
python -m Harness.cli --tasks-dir Harness/examples --pattern 'sample*.json'
```

运行一个多步工作流：

```bash
python -m Harness.cli --workflow Harness/examples/workflow_sample.json
```

查看可用本地工具：

```bash
python - <<'PY'
from Harness.tools import list_tools
print(list_tools())
PY
```

## 环境变量

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`，可选
- `OPENAI_MODEL`，默认 `gpt-4.1-mini`
- `HARNESS_RUNS_DIR`，默认 `Harness/runs`
- `HARNESS_MAX_WORKERS`，默认 `4`
- `HARNESS_MAX_RETRIES`，默认 `2`
- `HARNESS_RETRY_BACKOFF_SECONDS`，默认 `1.5`

## 你可以扩展的点

- 把 `examples/sample_task.json` 改成你的任务协议
- 在 `templates/system_prompt.md` 中写 Hermes Engineering 的固定系统规则
- 在 `runner.py` 中接入更多外部工具、模型切换
- 在 `cli.py` 中增加任务优先级、失败重试策略
- 在 `examples/` 中增加更多带 `checks` 的任务样例和 workflow
