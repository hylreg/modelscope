#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore
FM = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
KV = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.+?)\s*$")
QUOTE = re.compile(r"[\"“”](.+?)[\"“”]")
WORD = re.compile(r"[A-Za-z0-9_-]+")
T, M = 5, 2
K = ("简历", "自我介绍", "面试", "岗位", "JD", "润色", "生成")
def skill(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw
    if m := FM.match(raw.strip()):
        for line in m.group(1).splitlines():
            if kv := KV.match(line.strip()):
                meta[kv.group(1)] = kv.group(2).strip().strip('"').strip("'")
        body = m.group(2)
    return {"name": meta.get("name", path.parent.name), "desc": meta.get("description", ""), "path": path, "body": body, "trigs": [t.strip() for t in QUOTE.findall(raw)]}
def load(root: str) -> list[dict]:
    return [skill(p) for p in sorted(Path(root).glob("*/SKILL.md"))]
def route(skills: list[dict], q: str) -> tuple[dict | None, int, int]:
    ql = q.lower()
    qt = {w.lower() for w in WORD.findall(q)}
    ranked = sorted(((sum(5 for t in s["trigs"] if t.lower() in ql)
        + (3 if s["name"].lower() in ql else 0)
        + len(qt & {w.lower() for w in WORD.findall(s["desc"])})
        + sum(1 for k in K if k in q and k in s["desc"]), s) for s in skills), key=lambda x: x[0], reverse=True)
    if not ranked or ranked[0][0] <= 0:
        return None, 0, 0
    return ranked[0][1], ranked[0][0], ranked[1][0] if len(ranked) > 1 else 0
def pick(skills: list[dict], q: str, model: str) -> dict | None:
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None
    base = os.getenv("OPENAI_BASE_URL")
    try:
        resp = OpenAI(**({"base_url": base} if base else {})).responses.create(
            model=model,
            input=[
                {"role": "system", "content": "Pick one skill name or NONE."},
                {"role": "user", "content": "Skills:\n" + "\n".join(f"- {s['name']}: {s['desc']}" for s in skills) + f"\n\nRequest: {q}"},
            ],
        )
        name = getattr(resp, "output_text", "").strip()
        if not name:
            return None
        name = name.splitlines()[0].strip("`'\" ")
    except Exception:
        return None
    if name.upper() == "NONE":
        return None
    return next((s for s in skills if s["name"].lower() == name.lower()), None)
def run(s: dict, q: str, model: str) -> str:
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return "模型不可用"
    base = os.getenv("OPENAI_BASE_URL")
    try:
        resp = OpenAI(**({"base_url": base} if base else {})).responses.create(
            model=model,
            input=[{"role": "system", "content": s["body"]}, {"role": "user", "content": q}],
        )
        return getattr(resp, "output_text", "").strip() or str(resp)
    except Exception as e:
        return f"模型调用失败：{e}"
def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("query")
    a.add_argument("--skills-dir", default=str(Path(__file__).resolve().parents[1] / "Skills"))
    a.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    a.add_argument("--dry-run", action="store_true")
    args = a.parse_args()

    skills = load(args.skills_dir)
    s, top, second = route(skills, args.query)
    if not s:
        print("未匹配到 skill")
        return
    if top < T or top - second <= M:
        s = pick(skills, args.query, args.model) or s
    print(f"[router] {s['name']} score={top}")
    if not args.dry_run:
        print(run(s, args.query, args.model))
if __name__ == "__main__":
    main()
