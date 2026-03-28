#!/usr/bin/env python3
"""Build a structured creator knowledge base from normalized videos and optional analysis rows.

Usage:
python scripts/build_kb.py normalized_videos.json output_dir [video_analysis.jsonl]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from build_kb_from_md import build_kb as build_kb_from_rows


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_analysis_rows(path: Path | None) -> List[Dict[str, Any]]:
    if not path or not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict) and 'structured' in payload:
            rows.append(payload)
        else:
            structured = payload.get('analysis') if isinstance(payload, dict) else None
            if not isinstance(structured, dict):
                structured = payload
            video_id = (structured.get('video') or {}).get('video_id') or payload.get('video_id')
            rows.append({'video_id': str(video_id or 'unknown-video'), 'structured': structured, 'path': '', 'title': str(video_id or 'unknown-video')})
    return rows


def timestamp_range(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    vals = [str(x.get("create_time")) for x in items if x.get("create_time") is not None]
    if not vals:
        return {"earliest": None, "latest": None}
    return {"earliest": min(vals), "latest": max(vals)}


def make_creator(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    first = items[0] if items else {}
    return {
        "creator_key": first.get("author_sec_user_id") or first.get("author_unique_id") or "unknown-creator",
        "display_name": first.get("author_name") or "unknown-creator",
        "sec_user_id": first.get("author_sec_user_id"),
        "unique_id": first.get("author_unique_id"),
    }


def fallback_kb(videos: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        'creator': make_creator(videos),
        'dataset': {
            'video_count': len(videos),
            'analysis_count': 0,
            'time_range': timestamp_range(videos),
            'built_at': datetime.now(timezone.utc).isoformat(),
            'confidence': 'low',
            'source_breakdown': {'metadata_only': len(videos)},
        },
        'pattern_groups': {key: [] for key in ['goals', 'archetypes', 'hooks', 'beats', 'shots', 'dialogue', 'editing', 'persuasion', 'cta', 'reusable_formulas', 'risks']},
        'patterns': [],
        'video_index': [],
        'playbook': {
            'do_this': [],
            'test_this': [],
            'avoid_this': ['Do not make strong creative claims from metadata-only exports.'],
        },
    }


def write_outputs(output_dir: Path, kb: Dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "knowledge-base.json").write_text(json.dumps(kb, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "patterns.json").write_text(json.dumps(kb.get("patterns", []), ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "video-index.json").write_text(json.dumps(kb.get("video_index", []), ensure_ascii=False, indent=2), encoding="utf-8")
    sample = {
        "creator": kb.get("creator"),
        "dataset": kb.get("dataset"),
        "sample_video_ids": [row.get('video_id') for row in kb.get('video_index', [])][:100],
    }
    (output_dir / "sample-index.json").write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        f"# {kb['creator'].get('display_name', 'unknown')} Knowledge Base",
        '',
        '## Dataset',
        f"- video_count: {kb['dataset'].get('video_count')}",
        f"- analysis_count: {kb['dataset'].get('analysis_count')}",
        f"- confidence: {kb['dataset'].get('confidence')}",
        '',
        '## Top patterns',
    ]
    for pattern in kb.get('patterns', [])[:20]:
        lines.append(f"- [{pattern['category']}] {pattern['summary']} | evidence={pattern.get('evidence_count', len(pattern.get('evidence_video_ids', [])))} | confidence={pattern.get('confidence')}")
    lines.append('')
    lines.append('## Playbook')
    for section in ['do_this', 'test_this', 'avoid_this']:
        lines.append(f'### {section}')
        for item in kb.get('playbook', {}).get(section, []):
            lines.append(f'- {item}')
        lines.append('')
    (output_dir / 'knowledge-base.md').write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print("Usage: build_kb.py normalized_videos.json output_dir [video_analysis.jsonl]", file=sys.stderr)
        return 2
    videos = load_json(Path(sys.argv[1]))
    if not isinstance(videos, list):
        videos = videos.get("items") or []
    analysis_rows = load_analysis_rows(Path(sys.argv[3]) if len(sys.argv) == 4 else None)
    kb = build_kb_from_rows(analysis_rows) if analysis_rows else fallback_kb(videos)
    if videos and kb.get('creator', {}).get('display_name') == 'unknown-creator':
        kb['creator'] = make_creator(videos)
    if videos:
        kb['dataset']['video_count'] = len(videos)
        kb['dataset']['time_range'] = timestamp_range(videos)
    write_outputs(Path(sys.argv[2]), kb)
    print(f"Wrote structured KB to {sys.argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
