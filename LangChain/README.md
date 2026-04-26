# LangChain 示例

这是一个使用 LangChain 框架构建的 AI 代理示例，用于处理文学文本分析任务。

## 功能特点

- 使用 LangChain 构建 AI 代理
- 支持从 URL 获取文本内容进行分析
- 实现了普通代理和深度代理两种模式
- 可以分析《了不起的盖茨比》等文本内容

## 运行要求

- Python >= 3.12
- 已安装项目依赖

## 运行方法

使用 uv 运行（推荐）:

```bash
uv run LangChain/quickstart.py
```

或者，先确保项目已安装在开发模式下:

```bash
uv pip install -e .
uv run LangChain/quickstart.py
```

## 主要组件

- `fetch_text_from_url` 工具：从指定 URL 下载文档文本
- 系统提示词：指导 AI 如何处理文本分析任务
- 检查点机制：使用内存存储器保存代理状态

## 自定义

您可以修改系统提示词和内容部分来处理其他文本分析任务。