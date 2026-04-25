from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class HarnessConfig:
    api_key: str | None
    base_url: str | None
    model: str
    runs_dir: str


def load_config() -> HarnessConfig:
    return HarnessConfig(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        runs_dir=os.getenv("HARNESS_RUNS_DIR", "Harness/runs"),
    )
