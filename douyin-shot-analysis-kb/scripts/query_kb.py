#!/usr/bin/env python3
"""Query a creator knowledge base.

Usage:
python scripts/query_kb.py kb/creator-slug/knowledge-base.json "What hooks repeat most?"
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def answer_question(kb: dict, question: str) -> str:
    q = question.lower()
    patterns = kb.get("patterns", [])
    if "hook" in q or "开头" in q:
        hooks = [p for p in patterns if p.get("category") == "hook"]
        if not hooks:
            return "No hook patterns found in this knowledge base."
        lines = ["Top hook patterns:"]
        for p in hooks[:5]:
            lines.append(f"- {p.get('summary')} | evidence={len(p.get('evidence_video_ids', []))} | confidence={p.get('confidence')}")
        return "\n".join(lines)
        __TMP__
    if "镜头" in question or "shot" in q or "framing" in q:
        shots = [p for p in patterns if p.get("category") in {"shot_language", "camera", "framing"}]
        if not shots:
            return "No shot-language patterns found in this knowledge base."
        lines = ["Top shot-language patterns:"]
        for p in shots[:5]:
            lines.append(f"- {p.get('summary')} | evidence={len(p.get('evidence_video_ids', []))} | confidence={p.get('confidence')}")
        return "\n".join(lines)
        __TMP__
    playbook = kb.get("playbook", {})
    if playbook:
        return json.dumps(playbook, ensure_ascii=False, indent=2)
    return "Question not matched. Inspect patterns and playbook manually."


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: query_kb.py knowledge-base.json question", file=sys.stderr)
        return 2
    kb = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(answer_question(kb, sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
