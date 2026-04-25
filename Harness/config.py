from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class HarnessConfig:
    api_key: str | None
    base_url: str | None
    model: str
    runs_dir: str
    max_workers: int
    max_retries: int
    retry_backoff_seconds: float


def _parse_int(name: str, default: int, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        value = default
    else:
        try:
            value = int(raw)
        except ValueError:
            value = default
    if minimum is not None:
        value = max(minimum, value)
    return value


def _parse_float(name: str, default: float, minimum: float | None = None) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        value = default
    else:
        try:
            value = float(raw)
        except ValueError:
            value = default
    if minimum is not None:
        value = max(minimum, value)
    return value


def load_config() -> HarnessConfig:
    return HarnessConfig(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        runs_dir=os.getenv("HARNESS_RUNS_DIR", "Harness/runs"),
        max_workers=_parse_int("HARNESS_MAX_WORKERS", 4, minimum=1),
        max_retries=_parse_int("HARNESS_MAX_RETRIES", 2, minimum=0),
        retry_backoff_seconds=_parse_float("HARNESS_RETRY_BACKOFF_SECONDS", 1.5, minimum=0.0),
    )
