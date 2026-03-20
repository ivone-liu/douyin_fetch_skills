#!/usr/bin/env python3
"""Generate a simple script draft from a creator knowledge base.

Usage:
python scripts/generate_script.py kb/creator-slug/knowledge-base.json request.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def choose_patterns(kb: dict):
    patterns = kb.get("patterns", [])
    hooks = [p for p in patterns if p.get("category") == "hook_type"]
    structures = [p for p in patterns if p.get("category") in {"narrative_structure", "content_type"}]
    shots = [p for p in patterns if p.get("category") in {"shot_language", "camera", "framing"}]
    return hooks[:2], structures[:2], shots[:2]


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: generate_script.py knowledge-base.json request.json", file=sys.stderr)
        return 2
    kb = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    req = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    hooks, structures, shots = choose_patterns(kb)
    topic = req.get("topic") or req.get("product") or "未命名主题"
    audience = req.get("audience") or "泛用户"
    goal = req.get("goal") or "提高完播和互动"
    hook_line = f"你以为{topic}很难，其实很多人一开始就做错了第一步。"
    if hooks:
        hook_line = f"参考知识库中的 {hooks[0].get('summary')}，重写为: {hook_line}"
    shot_hint = shots[0].get("summary") if shots else "中近景稳定机位"
    structure_hint = structures[0].get("summary") if structures else "问题-拆解-建议-CTA"
    result = {
        "idea": {
            "topic_angle": topic,
            "audience": audience,
            "goal": goal,
        },
        "hook": {
            "line": hook_line,
            "visual": f"开头直接进入{shot_hint}",
            "source_patterns": [p.get("pattern_id") for p in hooks],
        },
        "beats": [
            {"beat": 1, "purpose": "setup", "script": f"先抛出{audience}最常见的误区。", "suggested_shot": shot_hint, "on_screen_text": "你可能一开始就做错了"},
            {"beat": 2, "purpose": "conflict", "script": f"指出继续这样做会导致什么损失或低效结果。", "suggested_shot": shot_hint, "on_screen_text": "问题不是不努力，而是方向错了"},
            {"beat": 3, "purpose": "proof", "script": f"给出一个具体方法或案例，沿用 {structure_hint} 的信息推进。", "suggested_shot": shot_hint, "on_screen_text": "这样改，才更容易有效"},
            {"beat": 4, "purpose": "payoff", "script": f"总结方法带来的结果，让用户看到收益。", "suggested_shot": shot_hint, "on_screen_text": "结果会完全不同"},
            {"beat": 5, "purpose": "cta", "script": "用一句低摩擦 CTA 邀请评论或收藏。", "suggested_shot": shot_hint, "on_screen_text": "想看下一条，评论区告诉我"},
        ],
        "cta": "评论区留言你的场景，我继续拆。",
        "fit_notes": [
            "This draft reuses high-frequency KB patterns instead of inventing style from scratch.",
            "It is adapted to the user's topic and audience rather than copied from the source creator."
        ],
        "risk_notes": [
            "This script is evidence-informed, not guaranteed to become a hit.",
            "Check whether the selected patterns depend on creator persona or delivery skill."
        ]
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
