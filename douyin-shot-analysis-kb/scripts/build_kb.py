#!/usr/bin/env python3
"""Build a first-pass markdown KB from normalized video metadata.

This script does not watch videos. It creates a scaffold based on metadata so the
analyst can fill in shot-language findings efficiently.

Usage:
python scripts/build_kb.py videos.json knowledge-base.md
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def load_items(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    return payload.get("items", [])


def safe_mean(values: List[float]) -> float | None:
    cleaned = [v for v in values if isinstance(v, (int, float))]
    if not cleaned:
        return None
    return round(statistics.mean(cleaned), 2)


def build_markdown(items: List[Dict[str, Any]]) -> str:
    author_name = next((x.get("author_name") for x in items if x.get("author_name")), "unknown-creator")
    total = len(items)
    durations = [x.get("duration_ms") for x in items if isinstance(x.get("duration_ms"), (int, float))]
    likes = [x.get("digg_count") for x in items if isinstance(x.get("digg_count"), (int, float))]
    shares = [x.get("share_count") for x in items if isinstance(x.get("share_count"), (int, float))]
    music = Counter(x.get("music_title") for x in items if x.get("music_title"))
    top_music = music.most_common(5)

    lines = []
    lines.append(f"# {author_name} Douyin Knowledge Base")
    lines.append("")
    lines.append("## Dataset overview")
    lines.append(f"- Total videos: {total}")
    if safe_mean(durations) is not None:
        lines.append(f"- Average duration_ms: {safe_mean(durations)}")
    if safe_mean(likes) is not None:
        lines.append(f"- Average digg_count: {safe_mean(likes)}")
    if safe_mean(shares) is not None:
        lines.append(f"- Average share_count: {safe_mean(shares)}")
    lines.append("")
    lines.append("## Top repeated music titles")
    if top_music:
        for title, freq in top_music:
            lines.append(f"- {title}: {freq}")
    else:
        lines.append("- No music metadata found")
    lines.append("")
    lines.append("## Manual analysis sections")
    lines.append("### Hooks")
    lines.append("- Fill in repeated opening strategies after watching a representative sample")
    lines.append("### Camera and framing")
    lines.append("- Fill in repeated shot distances, angles, and movement")
    lines.append("### Edit rhythm")
    lines.append("- Fill in transition speed, subtitle density, and cut frequency")
    lines.append("### Narrative structure")
    lines.append("- Fill in common scene order and payoff design")
    lines.append("### Packaging")
    lines.append("- Fill in cover style, title patterns, and series behavior")
    lines.append("### Reusable playbook")
    lines.append("- Turn observations into do this, test this, avoid this rules")
    lines.append("")
    lines.append("## Evidence sample")
    for item in items[:10]:
        lines.append(f"- {item.get('video_id')} | {item.get('create_time')} | {item.get('desc', '')[:80]}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: build_kb.py videos.json knowledge-base.md", file=sys.stderr)
        return 2
    items = load_items(Path(sys.argv[1]))
    md = build_markdown(items)
    Path(sys.argv[2]).write_text(md, encoding="utf-8")
    print(f"Wrote KB scaffold for {len(items)} videos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
