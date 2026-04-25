from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from .config import HarnessConfig
from .prompts import default_system_prompt, default_task_prompt


@dataclass(frozen=True)
class HarnessTask:
    name: str
    user_prompt: str
    system_prompt: str | None = None
    temperature: float = 0.2
    metadata: dict[str, Any] | None = None


def load_task(path: str | Path) -> HarnessTask:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return HarnessTask(
        name=raw.get("name", "unnamed-task"),
        user_prompt=raw["user_prompt"],
        system_prompt=raw.get("system_prompt"),
        temperature=float(raw.get("temperature", 0.2)),
        metadata=raw.get("metadata"),
    )


def render_task_prompt(task: HarnessTask) -> str:
    template = default_task_prompt()
    return template.format(
        task_name=task.name,
        user_prompt=task.user_prompt,
        metadata=json.dumps(task.metadata or {}, ensure_ascii=False, indent=2),
    )


def run_task(config: HarnessConfig, task: HarnessTask) -> str:
    if not config.api_key:
        return "未检测到 OPENAI_API_KEY，无法运行模型。"

    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    system_prompt = task.system_prompt or default_system_prompt()
    user_prompt = render_task_prompt(task)

    response = client.responses.create(
        model=config.model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=task.temperature,
    )
    return getattr(response, "output_text", "").strip() or str(response)

