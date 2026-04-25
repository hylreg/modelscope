#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
KV_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_-]*):\s*(.+?)\s*$")
QUOTE_RE = re.compile(r"[\"“”](.+?)[\"“”]")
WORD_RE = re.compile(r"[a-zA-Z0-9_-]+")
LLM_FALLBACK_THRESHOLD = 5
LLM_FALLBACK_MARGIN = 2


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    body: str
    triggers: list[str]


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = FRONTMATTER_RE.match(text.strip())
    if not m:
        return {}, text
    header = m.group(1)
    body = m.group(2)
    data: dict[str, str] = {}
    for line in header.splitlines():
        km = KV_RE.match(line.strip())
        if not km:
            continue
        key, value = km.groups()
        data[key] = value.strip().strip('"').strip("'")
    return data, body


def extract_triggers(text: str) -> list[str]:
    triggers = [m.group(1).strip() for m in QUOTE_RE.finditer(text)]
    seen: set[str] = set()
    out: list[str] = []
    for t in triggers:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def load_skills(skills_dir: Path) -> list[Skill]:
    skills: list[Skill] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        raw = skill_md.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)
        name = meta.get("name", skill_md.parent.name)
        description = meta.get("description", "")
        triggers = extract_triggers(raw)
        skills.append(
            Skill(
                name=name,
                description=description,
                path=skill_md,
                body=body,
                triggers=triggers,
            )
        )
    return skills


def tokenize_en(text: str) -> set[str]:
    return {w.lower() for w in WORD_RE.findall(text)}


def score_skill(skill: Skill, user_input: str) -> int:
    text = user_input.lower()
    score = 0

    # High-confidence signal: quoted trigger phrases from SKILL.md.
    for trig in skill.triggers:
        if trig and trig.lower() in text:
            score += 5

    # Medium signal: skill name.
    if skill.name.lower() in text:
        score += 3

    # Weak signal: English token overlap in description.
    desc_tokens = tokenize_en(skill.description)
    input_tokens = tokenize_en(user_input)
    score += len(desc_tokens & input_tokens)

    # Weak signal for common Chinese intent words.
    for kw in ("简历", "自我介绍", "面试", "岗位", "JD", "润色", "生成"):
        if kw in text and kw in skill.description:
            score += 1

    return score


def route_skill(skills: list[Skill], user_input: str) -> tuple[Skill | None, int]:
    if not skills:
        return None, 0
    ranked = sorted(
        ((score_skill(s, user_input), s) for s in skills),
        key=lambda x: x[0],
        reverse=True,
    )
    top_score, top_skill = ranked[0]
    if top_score <= 0:
        return None, 0
    return top_skill, top_score


def should_use_llm(skills: list[Skill], user_input: str, top_score: int) -> bool:
    if top_score < LLM_FALLBACK_THRESHOLD:
        return True
    ranked_scores = sorted((score_skill(s, user_input) for s in skills), reverse=True)
    return len(ranked_scores) > 1 and (ranked_scores[0] - ranked_scores[1]) <= LLM_FALLBACK_MARGIN


def classify_skill_with_llm(skills: list[Skill], user_input: str, model: str) -> Skill | None:
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None

    client_kwargs: dict[str, str] = {}
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        client_kwargs["base_url"] = base_url

    skill_list = "\n".join(f"- {skill.name}: {skill.description}" for skill in skills)
    prompt = (
        "Pick the single best matching skill for the user request.\n"
        "If none match, answer NONE.\n"
        "Return only the skill name or NONE.\n\n"
        f"Available skills:\n{skill_list}\n\n"
        f"User request: {user_input}"
    )

    try:
        client = OpenAI(**client_kwargs)
        resp = client.responses.create(model=model, input=prompt)
        raw = getattr(resp, "output_text", "").strip()
    except Exception:
        return None

    if not raw:
        return None

    normalized = raw.splitlines()[0].strip().strip("`'\" ")
    if normalized.upper() == "NONE":
        return None

    for skill in skills:
        if skill.name.lower() == normalized.lower():
            return skill
    return None


def call_skill_with_llm(skill: Skill, user_input: str, model: str) -> str:
    if OpenAI is None:
        return f"已匹配 skill: {skill.name}\n模型不可用"
    if not os.getenv("OPENAI_API_KEY"):
        return f"已匹配 skill: {skill.name}\n模型不可用"

    client_kwargs: dict[str, str] = {}
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        client_kwargs["base_url"] = base_url

    try:
        client = OpenAI(**client_kwargs)
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": skill.body},
                {"role": "user", "content": user_input},
            ],
        )
        return getattr(resp, "output_text", "").strip() or str(resp)
    except Exception as exc:
        return f"已匹配 skill: {skill.name}\n模型调用失败：{exc}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Minimal intent-driven skill agent"
    )
    parser.add_argument("query", help="User input")
    parser.add_argument(
        "--skills-dir",
        default=str(Path(__file__).resolve().parents[1] / "Skills"),
        help="Directory containing skill folders",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        help="Model used when OPENAI_API_KEY is present",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only route intent, do not call LLM",
    )
    args = parser.parse_args()

    skills = load_skills(Path(args.skills_dir))
    skill, score = route_skill(skills, args.query)
    if skill is None:
        print("未匹配到 skill")
        return

    if should_use_llm(skills, args.query, score):
        llm_skill = classify_skill_with_llm(skills, args.query, model=args.model)
        if llm_skill is not None:
            skill = llm_skill

    print(f"[router] skill={skill.name} score={score} path={skill.path}")
    if args.dry_run:
        return

    result = call_skill_with_llm(skill, args.query, model=args.model)
    print(result)


if __name__ == "__main__":
    main()
