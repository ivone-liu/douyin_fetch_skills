#!/usr/bin/env python3
"""Minimal helper for normalizing one Douyin video payload."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def normalize_single_video(payload: Dict[str, Any], source_input: str = "") -> Dict[str, Any]:
    data = payload.get("data") or payload
    author = data.get("author") or {}
    stats = data.get("statistics") or data.get("stats") or {}
    music = data.get("music") or {}
    video = data.get("video") or {}
    return {
        "video_id": data.get("aweme_id") or data.get("video_id") or data.get("id"),
        "desc": data.get("desc") or data.get("title") or "",
        "create_time": data.get("create_time"),
        "author_sec_user_id": author.get("sec_uid") or author.get("sec_user_id"),
        "author_unique_id": author.get("unique_id"),
        "author_name": author.get("nickname") or author.get("name"),
        "duration_ms": video.get("duration") or data.get("duration"),
        "digg_count": stats.get("digg_count") or stats.get("like_count"),
        "comment_count": stats.get("comment_count"),
        "collect_count": stats.get("collect_count"),
        "share_count": stats.get("share_count"),
        "play_count": stats.get("play_count"),
        "cover_url": ((video.get("cover") or {}).get("url_list") or [None])[0],
        "play_url": ((video.get("play_addr") or {}).get("url_list") or [None])[0],
        "music_title": music.get("title"),
        "music_author": music.get("author") or music.get("owner_nickname"),
        "is_pinned": data.get("is_top") or False,
        "source_input": source_input,
        "resolved_from": "single_video_endpoint",
        "crawl_time": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--source-input", default="")
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    normalized = normalize_single_video(payload, source_input=args.source_input)
    text = json.dumps(normalized, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
