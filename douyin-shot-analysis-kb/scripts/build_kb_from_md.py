#!/usr/bin/env python3
"""Build a structured creator KB from local markdown analysis documents.

Usage:
python scripts/build_kb_from_md.py ../data/creators/creator-slug/analysis_md ./kb/creator-slug
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)

PATTERN_SPECS: List[Tuple[str, str]] = [
    ("positioning.primary_goal", "goal"),
    ("positioning.content_archetype", "content_archetype"),
    ("hook.hook_type", "hook_type"),
    ("dialogue.delivery_style", "delivery_style"),
    ("dialogue.cta_type", "cta_type"),
    ("editing_packaging.pace", "editing_pace"),
    ("editing_packaging.subtitle_style", "subtitle_style"),
    ("reusable_patterns.opening_formula", "opening_formula"),
    ("reusable_patterns.structure_formula", "structure_formula"),
    ("reusable_patterns.shot_formula", "shot_formula"),
    ("reusable_patterns.dialogue_formula", "dialogue_formula"),
]

LIST_PATTERN_SPECS: List[Tuple[str, str]] = [
    ("positioning.sub_archetypes", "sub_archetype"),
    ("dialogue.rhetorical_moves", "rhetorical_move"),
    ("editing_packaging.transition_types", "transition_type"),
    ("editing_packaging.packaging_elements", "packaging_element"),
    ("persuasion.emotion_triggers", "emotion_trigger"),
    ("persuasion.credibility_signals", "credibility_signal"),
    ("persuasion.conversion_devices", "conversion_device"),
    ("risks_and_limits.risk_flags", "risk_flag"),
]


def nested_get(data: Dict[str, Any], dotted: str, default: Any = None) -> Any:
    node: Any = data
    for part in dotted.split('.'):
        if not isinstance(node, dict):
            return default
        node = node.get(part)
        if node is None:
            return default
    return node


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def extract_structured_json(text: str) -> Dict[str, Any]:
    for match in JSON_BLOCK_RE.finditer(text):
        candidate = match.group(1)
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and (data.get('analysis_version') or data.get('video') or data.get('positioning')):
            return data
    return {}


def fallback_line_value(text: str, prefixes: Iterable[str]) -> str | None:
    for raw in text.splitlines():
        line = raw.strip()
        for prefix in prefixes:
            if line.startswith(prefix):
                return line.split(':', 1)[1].strip()
    return None


def parse_md(path: Path) -> Dict[str, Any]:
    text = read_text(path)
    structured = extract_structured_json(text)
    video = structured.get('video') if isinstance(structured, dict) else None
    video_id = None
    if isinstance(video, dict):
        video_id = video.get('video_id')
    if not video_id:
        video_id = path.stem

    if not structured:
        structured = {
            'analysis_version': '0.5.0',
            'video': {
                'video_id': video_id,
                'desc': fallback_line_value(text, ['- desc:']) or '',
            },
            'analysis_scope': {
                'source_depth': 'metadata_only',
                'confidence': 'low',
                'notes': ['No structured JSON block was found. Parsed fallback line fields only.'],
            },
            'positioning': {
                'primary_goal': 'unknown',
                'secondary_goals': [],
                'content_archetype': 'unknown',
                'sub_archetypes': [],
                'target_audience': 'unknown',
            },
            'hook': {
                'hook_type': fallback_line_value(text, ['- hook_type:']) or 'unknown',
                'hook_text': '',
                'visual_hook': 'unknown',
                'emotion': 'unknown',
                'promise': '',
                'time_range': 'unknown',
            },
            'narrative': {
                'structure_formula': fallback_line_value(text, ['- script_structure:']) or 'unknown',
                'beats': [],
            },
            'shot_plan': {'dominant_style': 'unknown', 'shots': []},
            'dialogue': {'delivery_style': 'unknown', 'structure': 'unknown', 'rhetorical_moves': [], 'cta_type': 'unknown'},
            'editing_packaging': {'pace': 'unknown', 'subtitle_style': 'unknown', 'transition_types': [], 'packaging_elements': [], 'audio_strategy': 'unknown'},
            'persuasion': {'emotion_triggers': [], 'credibility_signals': [], 'conversion_devices': []},
            'reusable_patterns': {'opening_formula': '', 'structure_formula': '', 'shot_formula': '', 'dialogue_formula': '', 'applicable_scenarios': [], 'not_applicable_scenarios': []},
            'risks_and_limits': {'risk_flags': ['needs_manual_review'], 'unknowns': ['structured_json_missing']},
        }

    return {
        'video_id': str(video_id),
        'path': str(path),
        'structured': structured,
        'title': next((line.strip().lstrip('# ').strip() for line in text.splitlines() if line.strip().startswith('#')), path.stem),
    }


def video_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    data = row['structured']
    return {
        'video_id': row['video_id'],
        'primary_goal': nested_get(data, 'positioning.primary_goal', 'unknown'),
        'content_archetype': nested_get(data, 'positioning.content_archetype', 'unknown'),
        'hook_type': nested_get(data, 'hook.hook_type', 'unknown'),
        'structure_formula': nested_get(data, 'narrative.structure_formula', 'unknown'),
        'source_depth': nested_get(data, 'analysis_scope.source_depth', 'unknown'),
        'confidence': nested_get(data, 'analysis_scope.confidence', 'low'),
    }


def add_bucket(buckets: Dict[Tuple[str, str], List[Dict[str, Any]]], category: str, value: Any, row: Dict[str, Any], detail: str = '') -> None:
    if value in (None, '', 'unknown', 'needs_manual_review'):
        return
    buckets[(category, str(value))].append({'video_id': row['video_id'], 'detail': detail})


def harvest_patterns(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        data = row['structured']
        for dotted, category in PATTERN_SPECS:
            value = nested_get(data, dotted)
            add_bucket(buckets, category, value, row)
        for dotted, category in LIST_PATTERN_SPECS:
            values = nested_get(data, dotted, [])
            if isinstance(values, list):
                for value in values:
                    add_bucket(buckets, category, value, row)
        for beat in nested_get(data, 'narrative.beats', []) or []:
            if isinstance(beat, dict):
                add_bucket(buckets, 'beat_type', beat.get('beat_type'), row, beat.get('summary', ''))
                add_bucket(buckets, 'proof_type', beat.get('proof_type'), row, beat.get('summary', ''))
        for shot in nested_get(data, 'shot_plan.shots', []) or []:
            if isinstance(shot, dict):
                detail = shot.get('scene_task') or ''
                add_bucket(buckets, 'shot_size', shot.get('shot_size'), row, detail)
                add_bucket(buckets, 'camera_angle', shot.get('camera_angle'), row, detail)
                add_bucket(buckets, 'camera_movement', shot.get('camera_movement'), row, detail)
                add_bucket(buckets, 'scene_task', shot.get('scene_task'), row, detail)
    patterns: List[Dict[str, Any]] = []
    for idx, ((category, summary), evidence_rows) in enumerate(sorted(buckets.items(), key=lambda kv: len({x['video_id'] for x in kv[1]}), reverse=True), start=1):
        unique_video_ids = list(dict.fromkeys(item['video_id'] for item in evidence_rows if item.get('video_id')))
        sample_details = []
        seen_pairs = set()
        for item in evidence_rows:
            pair = (item['video_id'], item.get('detail') or '')
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            sample_details.append({'video_id': item['video_id'], 'detail': item.get('detail') or ''})
            if len(sample_details) >= 5:
                break
        confidence = round(min(0.95, 0.45 + 0.06 * len(unique_video_ids)), 2)
        patterns.append({
            'pattern_id': f'{category}_{idx:03d}',
            'category': category,
            'summary': summary,
            'evidence_video_ids': unique_video_ids,
            'confidence': confidence,
            'reusability_note': 'Derived from repeated structured video analyses.',
            'when_to_use': 'Use when your topic, goal, and delivery constraints match the evidence set.',
            'when_not_to_use': 'Do not copy this blindly when persona, production budget, or audience expectations are different.',
            'evidence_count': len(unique_video_ids),
            'sample_details': sample_details,
        })
    return patterns


def make_pattern_groups(patterns: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    group_map = {
        'goals': {'goal'},
        'archetypes': {'content_archetype', 'sub_archetype'},
        'hooks': {'hook_type', 'opening_formula'},
        'beats': {'beat_type', 'proof_type', 'structure_formula'},
        'shots': {'shot_size', 'camera_angle', 'camera_movement', 'scene_task', 'shot_formula'},
        'dialogue': {'delivery_style', 'rhetorical_move', 'dialogue_formula'},
        'editing': {'editing_pace', 'subtitle_style', 'transition_type', 'packaging_element'},
        'persuasion': {'emotion_trigger', 'credibility_signal', 'conversion_device'},
        'cta': {'cta_type'},
        'reusable_formulas': {'opening_formula', 'structure_formula', 'shot_formula', 'dialogue_formula'},
        'risks': {'risk_flag'},
    }
    result: Dict[str, List[Dict[str, Any]]] = {key: [] for key in group_map}
    for pattern in patterns:
        for group, categories in group_map.items():
            if pattern['category'] in categories:
                result[group].append(pattern)
    for group in result:
        result[group] = sorted(result[group], key=lambda item: item.get('evidence_count', 0), reverse=True)
    return result


def source_breakdown(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = Counter(nested_get(row['structured'], 'analysis_scope.source_depth', 'unknown') for row in rows)
    return dict(counts)


def playbook_from_patterns(pattern_groups: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[str]]:
    playbook = {'do_this': [], 'test_this': [], 'avoid_this': []}
    top_hooks = pattern_groups.get('hooks', [])[:3]
    top_structures = pattern_groups.get('beats', [])[:3]
    top_risks = pattern_groups.get('risks', [])[:3]
    for pattern in top_hooks:
        playbook['do_this'].append(f"Prioritize repeated hook pattern: {pattern['summary']}")
    for pattern in top_structures:
        playbook['test_this'].append(f"Test narrative pattern: {pattern['summary']}")
    if top_risks:
        for pattern in top_risks:
            playbook['avoid_this'].append(f"Watch risk pattern: {pattern['summary']}")
    else:
        playbook['avoid_this'].append('Do not assume metadata-only scaffolds equal proven creative laws.')
    return playbook


def dataset_confidence(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return 'low'
    scored = {'low': 1, 'medium': 2, 'high': 3}
    avg = sum(scored.get(nested_get(row['structured'], 'analysis_scope.confidence', 'low'), 1) for row in rows) / len(rows)
    if avg >= 2.4:
        return 'high'
    if avg >= 1.7:
        return 'medium'
    return 'low'


def earliest_latest(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    values = []
    for row in rows:
        value = nested_get(row['structured'], 'video.create_time')
        if value not in (None, ''):
            values.append(str(value))
    if not values:
        return {'earliest': None, 'latest': None}
    return {'earliest': min(values), 'latest': max(values)}


def write_outputs(out_dir: Path, kb: Dict[str, Any], video_rows: List[Dict[str, Any]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'knowledge-base.json').write_text(json.dumps(kb, ensure_ascii=False, indent=2), encoding='utf-8')
    (out_dir / 'patterns.json').write_text(json.dumps(kb.get('patterns', []), ensure_ascii=False, indent=2), encoding='utf-8')
    (out_dir / 'video-index.json').write_text(json.dumps(kb.get('video_index', []), ensure_ascii=False, indent=2), encoding='utf-8')
    sample_index = {
        'creator': kb.get('creator'),
        'dataset': kb.get('dataset'),
        'sample_video_ids': [row['video_id'] for row in video_rows[:100]],
    }
    (out_dir / 'sample-index.json').write_text(json.dumps(sample_index, ensure_ascii=False, indent=2), encoding='utf-8')

    md_lines = [
        f"# {kb['creator'].get('display_name', 'unknown')} Knowledge Base",
        '',
        '## Dataset',
        f"- video_count: {kb['dataset'].get('video_count')}",
        f"- analysis_count: {kb['dataset'].get('analysis_count')}",
        f"- confidence: {kb['dataset'].get('confidence')}",
        f"- source_breakdown: {json.dumps(kb['dataset'].get('source_breakdown', {}), ensure_ascii=False)}",
        '',
        '## Top pattern groups',
    ]
    for group, patterns in kb.get('pattern_groups', {}).items():
        if not patterns:
            continue
        md_lines.append(f"### {group}")
        for pattern in patterns[:5]:
            md_lines.append(f"- [{pattern['category']}] {pattern['summary']} | evidence={pattern.get('evidence_count')} | confidence={pattern.get('confidence')}")
        md_lines.append('')
    md_lines.append('## Playbook')
    for section in ['do_this', 'test_this', 'avoid_this']:
        md_lines.append(f"### {section}")
        for item in kb.get('playbook', {}).get(section, []):
            md_lines.append(f'- {item}')
        md_lines.append('')
    (out_dir / 'knowledge-base.md').write_text('\n'.join(md_lines).rstrip() + '\n', encoding='utf-8')


def build_kb(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    video_index = [video_summary(row) for row in rows]
    patterns = harvest_patterns(rows)
    pattern_groups = make_pattern_groups(patterns)
    first_video = rows[0]['structured'].get('video', {}) if rows else {}
    creator = {
        'creator_key': first_video.get('author_unique_id') or first_video.get('author_name') or 'unknown-creator',
        'display_name': first_video.get('author_name') or 'unknown-creator',
        'sec_user_id': first_video.get('author_sec_user_id'),
        'unique_id': first_video.get('author_unique_id'),
    }
    return {
        'creator': creator,
        'dataset': {
            'video_count': len(rows),
            'analysis_count': len(rows),
            'time_range': earliest_latest(rows),
            'built_at': datetime.now(timezone.utc).isoformat(),
            'confidence': dataset_confidence(rows),
            'source_breakdown': source_breakdown(rows),
        },
        'pattern_groups': pattern_groups,
        'patterns': patterns,
        'video_index': video_index,
        'playbook': playbook_from_patterns(pattern_groups),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print('Usage: build_kb_from_md.py md_dir output_dir', file=sys.stderr)
        return 2
    md_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    rows = [parse_md(p) for p in sorted(md_dir.rglob('*.md'))]
    kb = build_kb(rows)
    write_outputs(out_dir, kb, rows)
    print(f'Wrote structured markdown-derived KB to {out_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
