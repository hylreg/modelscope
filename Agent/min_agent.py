#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
KEY_VALUE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.+?)\s*$")
QUOTED_TEXT_RE = re.compile(r"[\"“”](.+?)[\"“”]")
WORD_RE = re.compile(r"[A-Za-z0-9_-]+")

ROUTER_SCORE_THRESHOLD = 5
ROUTER_MARGIN_THRESHOLD = 2
ROUTER_KEYWORDS = ("简历", "自我介绍", "面试", "岗位", "JD", "润色", "生成")


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    path: Path
    body: str
    triggers: tuple[str, ...]


def parse_skill(path: Path) -> Skill:
    """Read one SKILL.md file and extract the metadata needed by the router."""
    raw = path.read_text(encoding="utf-8")
    metadata, body = _parse_front_matter(raw)
    triggers = tuple(t.strip() for t in QUOTED_TEXT_RE.findall(raw))

    return Skill(
        name=metadata.get("name", path.parent.name),
        description=metadata.get("description", ""),
        path=path,
        body=body,
        triggers=triggers,
    )


def _parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    metadata: dict[str, str] = {}
    body = raw

    if match := FRONT_MATTER_RE.match(raw.strip()):
        for line in match.group(1).splitlines():
            if key_value := KEY_VALUE_RE.match(line.strip()):
                metadata[key_value.group(1)] = key_value.group(2).strip().strip('"').strip("'")
        body = match.group(2)

    return metadata, body


def load_skills(root: str) -> list[Skill]:
    """Load every `*/SKILL.md` under the configured skills directory."""
    return [parse_skill(path) for path in sorted(Path(root).glob("*/SKILL.md"))]


def score_skill(skill: Skill, query: str) -> int:
    """Score one skill against a user query using simple lexical heuristics."""
    query_lower = query.lower()
    query_words = {word.lower() for word in WORD_RE.findall(query)}
    description_words = {word.lower() for word in WORD_RE.findall(skill.description)}

    score = 0
    score += sum(5 for trigger in skill.triggers if trigger.lower() in query_lower)
    score += 3 if skill.name.lower() in query_lower else 0
    score += len(query_words & description_words)
    score += sum(1 for keyword in ROUTER_KEYWORDS if keyword in query and keyword in skill.description)
    return score


def route(skills: Iterable[Skill], query: str) -> tuple[Skill | None, int, int]:
    """Pick the highest-scoring skill and return its score plus runner-up score."""
    ranked = sorted(
        ((score_skill(skill, query), skill) for skill in skills),
        key=lambda item: item[0],
        reverse=True,
    )
    if not ranked or ranked[0][0] <= 0:
        return None, 0, 0

    top_score, top_skill = ranked[0]
    second_score = ranked[1][0] if len(ranked) > 1 else 0
    return top_skill, top_score, second_score


def pick_skill_with_llm(skills: list[Skill], query: str, model: str) -> Skill | None:
    """Use an LLM to choose a skill when routing is ambiguous."""
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None

    base_url = os.getenv("OPENAI_BASE_URL")
    client = OpenAI(**({"base_url": base_url} if base_url else {}))

    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": "Pick one skill name or NONE."},
                {
                    "role": "user",
                    "content": "Skills:\n"
                    + "\n".join(f"- {skill.name}: {skill.description}" for skill in skills)
                    + f"\n\nRequest: {query}",
                },
            ],
        )
        name = getattr(response, "output_text", "").strip()
    except Exception:
        return None

    if not name:
        return None

    candidate = name.splitlines()[0].strip("`'\" ")
    if candidate.upper() == "NONE":
        return None
    return next((skill for skill in skills if skill.name.lower() == candidate.lower()), None)


def run_skill(skill: Skill, query: str, model: str) -> str:
    """Execute the selected skill by sending its body as system prompt."""
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return "模型不可用"

    base_url = os.getenv("OPENAI_BASE_URL")
    client = OpenAI(**({"base_url": base_url} if base_url else {}))

    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": skill.body},
                {"role": "user", "content": query},
            ],
        )
        return getattr(response, "output_text", "").strip() or str(response)
    except Exception as exc:
        return f"模型调用失败：{exc}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--skills-dir", default=str(Path(__file__).resolve().parents[1] / "Skills"))
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    skills = load_skills(args.skills_dir)
    selected_skill, top_score, second_score = route(skills, args.query)
    if not selected_skill:
        print("未匹配到 skill")
        return

    if top_score < ROUTER_SCORE_THRESHOLD or top_score - second_score <= ROUTER_MARGIN_THRESHOLD:
        selected_skill = pick_skill_with_llm(skills, args.query, args.model) or selected_skill

    print(f"[router] {selected_skill.name} score={top_score}")
    if not args.dry_run:
        print(run_skill(selected_skill, args.query, args.model))


if __name__ == "__main__":
    main()
