#!/usr/bin/env python3
"""Normalize TikHub Douyin video items into a stable schema.

Usage:
python scripts/normalize_videos.py input.json output.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


def pick(dct: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in dct and dct[key] not in (None, ""):
            return dct[key]
    return None


def normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    author = item.get("author") or {}
    stats = item.get("statistics") or item.get("stats") or {}
    music = item.get("music") or {}
    now = datetime.now(timezone.utc).isoformat()

    return {
        "video_id": pick(item, "aweme_id", "video_id", "id"),
        "desc": pick(item, "desc", "title"),
        "create_time": pick(item, "create_time"),
        "author_sec_user_id": pick(author, "sec_uid", "sec_user_id"),
        "author_unique_id": pick(author, "unique_id"),
        "author_name": pick(author, "nickname", "name"),
        "duration_ms": pick(item, "duration", "duration_ms"),
        "digg_count": pick(stats, "digg_count", "like_count"),
        "comment_count": pick(stats, "comment_count"),
        "collect_count": pick(stats, "collect_count", "favorite_count"),
        "share_count": pick(stats, "share_count"),
        "play_count": pick(stats, "play_count", "view_count"),
        "cover_url": pick(item, "cover_url", "cover", "dynamic_cover"),
        "play_url": pick(item, "play_url", "wm_play_url", "nowm_play_url"),
        "music_title": pick(music, "title"),
        "music_author": pick(music, "author", "owner_nickname"),
        "mix_id": pick(item, "mix_id"),
        "is_pinned": bool(pick(item, "is_top", "is_pinned") or False),
        "crawl_time": now,
    }


def unique_by_video_id(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result: List[Dict[str, Any]] = []
    for item in items:
        key = item.get("video_id")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: normalize_videos.py input.json output.json", file=sys.stderr)
        return 2

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    payload = json.loads(src.read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else payload.get("items") or payload.get("aweme_list") or []
    normalized = unique_by_video_id(normalize_item(item) for item in items)
    dst.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(normalized)} normalized items to {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
