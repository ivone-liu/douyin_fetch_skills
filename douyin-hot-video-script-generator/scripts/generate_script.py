#!/usr/bin/env python3
"""Generate a structured script draft from a creator knowledge base.

Usage:
python scripts/generate_script.py kb/creator-slug/knowledge-base.json request.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def ranked_patterns(kb: dict, categories: List[str]) -> List[dict]:
    matched = [p for p in kb.get('patterns', []) if p.get('category') in set(categories)]
    return sorted(matched, key=lambda item: item.get('evidence_count', len(item.get('evidence_video_ids', []))), reverse=True)


def first_summary(patterns: List[dict], fallback: str) -> str:
    return patterns[0].get('summary') if patterns else fallback


def collect_ids(*pattern_groups: List[dict]) -> List[str]:
    result = []
    for group in pattern_groups:
        for pattern in group:
            pid = pattern.get('pattern_id')
            if pid and pid not in result:
                result.append(pid)
    return result


def build_hook_line(topic: str, hook_hint: str) -> str:
    hook_hint_lower = hook_hint.lower()
    if 'question' in hook_hint_lower or '问题' in hook_hint:
        return f"为什么你明明在做{topic}，结果还是没效果？问题不在努力，而在起手动作。"
    if 'promise' in hook_hint_lower or '公式' in hook_hint or '承诺' in hook_hint:
        return f"把{topic}先改这一步，你后面的结果会完全不一样。"
    if 'story' in hook_hint_lower or '故事' in hook_hint:
        return f"我以前也以为{topic}只要多做就行，后来才发现自己一直做反了。"
    return f"你以为{topic}的重点在后面，其实一开始那一下就决定了结果。"


def main() -> int:
    if len(sys.argv) != 3:
        print('Usage: generate_script.py knowledge-base.json request.json', file=sys.stderr)
        return 2

    kb = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    req = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))

    topic = req.get('topic') or req.get('product') or '未命名主题'
    audience = req.get('audience') or '泛用户'
    goal = req.get('goal') or '提高完播和互动'
    duration_target_sec = int(req.get('duration_target_sec') or 30)
    constraints = req.get('constraints') or []
    if isinstance(constraints, str):
        constraints = [constraints]

    hook_patterns = ranked_patterns(kb, ['hook_type', 'opening_formula'])[:3]
    structure_patterns = ranked_patterns(kb, ['content_archetype', 'structure_formula', 'beat_type', 'proof_type'])[:4]
    shot_patterns = ranked_patterns(kb, ['shot_size', 'camera_movement', 'scene_task', 'shot_formula'])[:4]
    dialogue_patterns = ranked_patterns(kb, ['delivery_style', 'rhetorical_move', 'dialogue_formula', 'cta_type'])[:4]
    packaging_patterns = ranked_patterns(kb, ['editing_pace', 'subtitle_style', 'transition_type', 'packaging_element'])[:4]
    risk_patterns = ranked_patterns(kb, ['risk_flag'])[:3]

    hook_hint = first_summary(hook_patterns, 'direct_statement')
    structure_hint = first_summary(structure_patterns, 'problem -> explanation -> action -> cta')
    shot_hint = first_summary(shot_patterns, '中近景稳定机位 + 关键处切特写')
    dialogue_hint = first_summary(dialogue_patterns, '先戳误区，再给动作')
    cta_hint = first_summary([p for p in dialogue_patterns if p.get('category') == 'cta_type'], 'comment')

    hook_line = build_hook_line(topic, hook_hint)
    source_pattern_ids = collect_ids(hook_patterns, structure_patterns, shot_patterns, dialogue_patterns)

    beats = [
        {
            'beat': 1,
            'purpose': 'hook',
            'script': hook_line,
            'suggested_shot': shot_hint,
            'on_screen_text': f'{topic}别再起手就做错',
            'dialogue_move': dialogue_hint,
        },
        {
            'beat': 2,
            'purpose': 'setup',
            'script': f'先把{audience}最常犯的错误说穿，让用户立刻对号入座。',
            'suggested_shot': shot_hint,
            'on_screen_text': '很多人错在第一步',
            'dialogue_move': '替观众说话',
        },
        {
            'beat': 3,
            'purpose': 'conflict',
            'script': '把错误继续下去的代价讲清楚，不要只说不好，要说会损失什么。',
            'suggested_shot': shot_hint,
            'on_screen_text': '继续这样做，结果只会更差',
            'dialogue_move': '制造代价',
        },
        {
            'beat': 4,
            'purpose': 'proof',
            'script': f'按照 {structure_hint} 的方式给出一个动作、案例或对比证明。',
            'suggested_shot': shot_hint,
            'on_screen_text': '先这样改，再看结果',
            'dialogue_move': '给证据',
        },
        {
            'beat': 5,
            'purpose': 'payoff',
            'script': f'总结用户做完这个动作后会得到的具体收益，让结果可感知。',
            'suggested_shot': shot_hint,
            'on_screen_text': '改完之后，结果会很不一样',
            'dialogue_move': '结果承诺',
        },
        {
            'beat': 6,
            'purpose': 'cta',
            'script': f'使用低摩擦 CTA 收尾，优先采用 {cta_hint} 风格。',
            'suggested_shot': shot_hint,
            'on_screen_text': '要下一条模板，评论区留关键词',
            'dialogue_move': '明确动作指令',
        },
    ]

    shot_plan = [
        {'shot_id': 1, 'purpose': 'hook', 'shot_hint': shot_hint, 'movement_hint': first_summary(shot_patterns, 'static'), 'transition_hint': first_summary(packaging_patterns, 'hard_cut')},
        {'shot_id': 2, 'purpose': 'problem detail', 'shot_hint': '中景口播或问题示范', 'movement_hint': first_summary(shot_patterns[1:], 'static'), 'transition_hint': first_summary(packaging_patterns[1:], 'hard_cut')},
        {'shot_id': 3, 'purpose': 'proof/demo', 'shot_hint': '细节特写或 before-after 对比', 'movement_hint': first_summary(shot_patterns[2:], 'push'), 'transition_hint': first_summary(packaging_patterns[2:], 'match_cut')},
    ]

    result = {
        'idea': {
            'topic_angle': topic,
            'audience': audience,
            'goal': goal,
            'duration_target_sec': duration_target_sec,
            'constraints': constraints,
        },
        'positioning': {
            'content_archetype': first_summary([p for p in structure_patterns if p.get('category') == 'content_archetype'], 'educational'),
            'delivery_style': first_summary([p for p in dialogue_patterns if p.get('category') == 'delivery_style'], 'direct_explainer'),
            'evidence_patterns': source_pattern_ids,
        },
        'hook': {
            'line': hook_line,
            'visual': f'开头直接进入 {shot_hint}',
            'source_patterns': [p.get('pattern_id') for p in hook_patterns],
        },
        'beats': beats,
        'shot_plan': shot_plan,
        'cta': '评论区留言你的场景，我继续拆。',
        'fit_notes': [
            f'Core structure grounded in KB pattern: {structure_hint}',
            f'Shot suggestion grounded in KB pattern: {shot_hint}',
            'This draft adapts patterns instead of copying any single source post.'
        ],
        'risk_notes': [
            'Evidence-informed does not mean guaranteed to become a hit.',
            'Check whether the selected patterns depend on creator persona, face expression, or editing skill.',
            *([f"Risk flag from KB: {pattern['summary']}" for pattern in risk_patterns] or [])
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
