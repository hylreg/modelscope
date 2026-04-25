from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"


def load_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def default_system_prompt() -> str:
    return load_template("system_prompt.md")


def default_task_prompt() -> str:
    return load_template("task_prompt.md")


def default_workflow_prompt() -> str:
    return load_template("workflow_prompt.md")
