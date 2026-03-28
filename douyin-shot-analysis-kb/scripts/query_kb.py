#!/usr/bin/env python3
"""Query a creator knowledge base.

Usage:
python scripts/query_kb.py kb/creator-slug/knowledge-base.json "What hooks repeat most?"
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List


def choose_patterns(kb: dict, categories: List[str]) -> List[dict]:
    patterns = kb.get('patterns', [])
    matched = [p for p in patterns if p.get('category') in set(categories)]
    return sorted(matched, key=lambda item: item.get('evidence_count', len(item.get('evidence_video_ids', []))), reverse=True)


def format_patterns(title: str, patterns: List[dict]) -> str:
    if not patterns:
        return f'No matching patterns found for {title}.'
    lines = [title]
    for pattern in patterns[:8]:
        lines.append(f"- [{pattern.get('category')}] {pattern.get('summary')} | evidence={pattern.get('evidence_count', len(pattern.get('evidence_video_ids', [])))} | confidence={pattern.get('confidence')}")
    return '\n'.join(lines)


def answer_question(kb: Dict[str, object], question: str) -> str:
    q = question.lower()
    if 'hook' in q or '开头' in question or '钩子' in question:
        return format_patterns('Top hook patterns:', choose_patterns(kb, ['hook_type', 'opening_formula']))
    if '镜头' in question or 'shot' in q or 'framing' in q or '运镜' in question:
        return format_patterns('Top shot-language patterns:', choose_patterns(kb, ['shot_size', 'camera_angle', 'camera_movement', 'scene_task', 'shot_formula']))
    if '结构' in question or 'beat' in q or '节奏' in question:
        return format_patterns('Top structural patterns:', choose_patterns(kb, ['content_archetype', 'structure_formula', 'beat_type', 'proof_type', 'editing_pace']))
    if '话术' in question or 'dialogue' in q or '文案' in question:
        return format_patterns('Top dialogue patterns:', choose_patterns(kb, ['delivery_style', 'rhetorical_move', 'dialogue_formula', 'cta_type']))
    if '转化' in question or 'persuasion' in q or '说服' in question:
        return format_patterns('Top persuasion patterns:', choose_patterns(kb, ['emotion_trigger', 'credibility_signal', 'conversion_device', 'cta_type']))
    if '风险' in question or '不要' in question or 'avoid' in q:
        playbook = kb.get('playbook', {})
        avoid_items = playbook.get('avoid_this', []) if isinstance(playbook, dict) else []
        lines = ['Top avoid notes:']
        for item in avoid_items[:8]:
            lines.append(f'- {item}')
        return '\n'.join(lines)
    playbook = kb.get('playbook', {})
    if playbook:
        return json.dumps(playbook, ensure_ascii=False, indent=2)
    return 'Question not matched. Inspect patterns and playbook manually.'


def main() -> int:
    if len(sys.argv) != 3:
        print('Usage: query_kb.py knowledge-base.json question', file=sys.stderr)
        return 2
    kb = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    print(answer_question(kb, sys.argv[2]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
