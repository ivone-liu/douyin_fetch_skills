#!/usr/bin/env python3
"""Build a structured creator knowledge base from normalized videos and optional analysis rows.

Usage:
python scripts/build_kb.py normalized_videos.json output_dir [video_analysis.jsonl]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


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
        rows.append(json.loads(line))
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


def patterns_from_analysis(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[tuple, List[str]] = defaultdict(list)
    for row in rows:
        vid = row.get("video_id")
        for category in ["hook_type", "content_type", "narrative_structure"]:
            value = row.get(category)
            if value:
                buckets[(category, str(value))].append(vid)
        for category, source in [("shot_language", row.get("shot_style")), ("editing_rhythm", row.get("editing_style")), ("emotion_tone", row.get("emotion_tone"))]:
            if isinstance(source, list):
                for value in source:
                    if value:
                        buckets[(category, str(value))].append(vid)
    patterns = []
    for idx, ((category, summary), evidence) in enumerate(sorted(buckets.items(), key=lambda kv: len(kv[1]), reverse=True), start=1):
        uniq = list(dict.fromkeys([x for x in evidence if x]))
        confidence = round(min(0.95, 0.4 + 0.05 * len(uniq)), 2)
        patterns.append({
            "pattern_id": f"{category}_{idx:03d}",
            "category": category,
            "summary": summary,
            "evidence_video_ids": uniq,
            "confidence": confidence,
            "reusability_note": "Derived from repeated analysis labels.",
            "when_to_use": "Use when the target content goal matches the creator pattern.",
            "when_not_to_use": "Do not copy blindly when audience, product, or tone is different.",
        })
    return patterns


def heuristic_playbook(items: List[Dict[str, Any]], patterns: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    playbook = {"do_this": [], "test_this": [], "avoid_this": []}
    if items:
        playbook["do_this"].append("Keep a stable creator-specific format instead of changing style every post.")
    top_hooks = [p for p in patterns if p.get("category") == "hook_type"][:3]
    for p in top_hooks:
        playbook["test_this"].append(f"Test hook pattern: {p.get('summary')}")
    if not patterns:
        playbook["avoid_this"].append("Do not make strong creative claims from metadata only.")
    else:
        playbook["avoid_this"].append("Do not reuse high-frequency patterns without checking fit for audience and product.")
    return playbook


def write_outputs(output_dir: Path, kb: Dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "knowledge-base.json").write_text(json.dumps(kb, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "patterns.json").write_text(json.dumps(kb.get("patterns", []), ensure_ascii=False, indent=2), encoding="utf-8")
    sample = {
        "creator": kb.get("creator"),
        "dataset": kb.get("dataset"),
        "sample_video_ids": sorted({vid for p in kb.get("patterns", []) for vid in p.get("evidence_video_ids", [])})[:100],
    }
    (output_dir / "sample-index.json").write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    md = []
    md.append(f"# {kb['creator'].get('display_name', 'unknown')} Knowledge Base")
    md.append("")
    md.append("## Dataset")
    md.append(f"- video_count: {kb['dataset'].get('video_count')}")
    md.append(f"- analysis_count: {kb['dataset'].get('analysis_count')}")
    md.append(f"- confidence: {kb['dataset'].get('confidence')}")
    md.append("")
    md.append("## Top patterns")
    for p in kb.get("patterns", [])[:15]:
        md.append(f"- [{p['category']}] {p['summary']} | evidence={len(p.get('evidence_video_ids', []))} | confidence={p.get('confidence')}")
    md.append("")
    md.append("## Playbook")
    for section in ["do_this", "test_this", "avoid_this"]:
        md.append(f"### {section}")
        for item in kb.get("playbook", {}).get(section, []):
            md.append(f"- {item}")
    (output_dir / "knowledge-base.md").write_text("
".join(md), encoding="utf-8")


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print("Usage: build_kb.py normalized_videos.json output_dir [video_analysis.jsonl]", file=sys.stderr)
        return 2
    videos = load_json(Path(sys.argv[1]))
    if not isinstance(videos, list):
        videos = videos.get("items") or []
    analysis_rows = load_analysis_rows(Path(sys.argv[3]) if len(sys.argv) == 4 else None)
    patterns = patterns_from_analysis(analysis_rows)
    confidence = "high" if analysis_rows and len(analysis_rows) >= max(5, len(videos) // 5) else ("medium" if analysis_rows else "low")
    kb = {
        "creator": make_creator(videos),
        "dataset": {
            "video_count": len(videos),
            "analysis_count": len(analysis_rows),
            "time_range": timestamp_range(videos),
            "built_at": datetime.now(timezone.utc).isoformat(),
            "confidence": confidence,
        },
        "patterns": patterns,
        "playbook": heuristic_playbook(videos, patterns),
    }
    write_outputs(Path(sys.argv[2]), kb)
    print(f"Wrote structured KB to {sys.argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
