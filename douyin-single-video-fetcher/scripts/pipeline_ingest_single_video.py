#!/usr/bin/env python3
"""End-to-end single-video ingestion pipeline.

What it does:
1. read a raw TikHub single-video payload
2. save raw payload to local JSON
3. normalize key fields
4. upsert searchable fields into MySQL
5. download video and music into grouped local directories
6. generate one markdown analysis file per video
7. update MySQL with local paths and statuses

Example:
python scripts/pipeline_ingest_single_video.py raw_payload.json \
  --storage-root ./storage \
  --mysql-dsn 'mysql://user:pass@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4' \
  --endpoint-name fetch_one_video_v2 \
  --source-input 'https://v.douyin.com/xxxx/'
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

try:
    import pymysql  # type: ignore
except Exception:
    pymysql = None

from fetch_single_video import normalize_single_video


@dataclass
class PipelineContext:
    storage_root: Path
    mysql_dsn: Optional[str]
    endpoint_name: str
    source_input: str


def slugify(value: str) -> str:
    value = (value or 'unknown').strip().lower()
    value = re.sub(r'[^a-z0-9\u4e00-\u9fff_-]+', '-', value)
    value = re.sub(r'-+', '-', value).strip('-')
    return value or 'unknown'


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_dir() -> str:
    return datetime.now().strftime('%Y-%m-%d')


def nested_get_first_url(obj: Any, preferred_keys: Iterable[str]) -> Optional[str]:
    candidates: list[tuple[str, str]] = []

    def walk(node: Any, path: str = '') -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                new_path = f'{path}.{k}' if path else k
                if isinstance(v, str) and v.startswith('http'):
                    candidates.append((new_path, v))
                else:
                    walk(v, new_path)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f'{path}[{i}]')

    walk(obj)
    for key in preferred_keys:
        for path, value in candidates:
            if key in path:
                return value
    return candidates[0][1] if candidates else None


def extract_music_meta(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.get('data') or payload
    music = data.get('music') or {}
    play_url = nested_get_first_url(music, ['play_url', 'play_addr', 'url_list', 'uri'])
    return {
        'music_id': music.get('id') or music.get('mid') or music.get('music_id') or music.get('id_str'),
        'title': music.get('title') or music.get('album') or 'unknown',
        'author_name': music.get('author') or music.get('owner_nickname') or music.get('author_name'),
        'duration_ms': music.get('duration') or music.get('duration_ms'),
        'play_url': play_url,
    }


def choose_extension(url: Optional[str], content_type: Optional[str], fallback: str) -> str:
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(';')[0].strip())
        if ext:
            return ext
    if url:
        path = urlparse(url).path
        ext = Path(path).suffix
        if ext:
            return ext
    return fallback


def save_raw_payload(payload: Dict[str, Any], ctx: PipelineContext, video_id: str) -> Path:
    out = ctx.storage_root / 'raw_api' / 'douyin_single_video' / today_dir()
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'{video_id}.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def save_normalized(normalized: Dict[str, Any], ctx: PipelineContext, video_id: str) -> Path:
    out = ctx.storage_root / 'normalized' / 'douyin_single_video'
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'{video_id}.json'
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def download_asset(url: Optional[str], path: Path) -> Optional[Path]:
    if not url:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=60) as resp:
        content_type = resp.headers.get('Content-Type')
        if path.suffix == '':
            path = path.with_suffix(choose_extension(url, content_type, '.bin'))
        with open(path, 'wb') as f:
            shutil.copyfileobj(resp, f)
    return path


def run_ffprobe(path: Optional[Path]) -> Dict[str, Any]:
    if not path or not path.exists():
        return {}
    if shutil.which('ffprobe') is None:
        return {'available': False, 'reason': 'ffprobe_not_installed'}
    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(path)]
    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return {'available': True, 'data': json.loads(raw.decode('utf-8'))}
    except Exception as exc:
        return {'available': False, 'reason': str(exc)}


def infer_script_shape(desc: str) -> Dict[str, Any]:
    desc = desc or ''
    if any(x in desc for x in ['为什么', '为何', '到底', '?', '？']):
        hook = 'question_hook'
    elif any(x in desc for x in ['3个', '5个', '10个', '步骤', '方法']):
        hook = 'numbered_promise'
    elif len(desc) <= 12:
        hook = 'short_direct_hook'
    else:
        hook = 'statement_hook'

    if any(x in desc for x in ['教程', '步骤', '方法', '怎么做']):
        structure = 'tutorial_breakdown'
    elif any(x in desc for x in ['我发现', '以前', '后来']):
        structure = 'experience_story'
    else:
        structure = 'statement_then_explanation'
    return {'hook_type': hook, 'script_structure': structure}


def infer_media_notes(video_probe: Dict[str, Any], music_probe: Dict[str, Any]) -> Dict[str, Any]:
    notes = {
        'shot_language_guess': 'unknown',
        'editing_rhythm_guess': 'unknown',
        'audio_notes': [],
        'confidence': 'low',
    }
    vdata = (video_probe or {}).get('data') or {}
    streams = vdata.get('streams') or []
    vstreams = [s for s in streams if s.get('codec_type') == 'video']
    if vstreams:
        width = vstreams[0].get('width')
        height = vstreams[0].get('height')
        fps_expr = vstreams[0].get('avg_frame_rate') or vstreams[0].get('r_frame_rate')
        notes['audio_notes'].append(f'video_resolution={width}x{height}')
        notes['audio_notes'].append(f'video_fps={fps_expr}')
        notes['shot_language_guess'] = 'needs_visual_model_or_manual_review'
        notes['editing_rhythm_guess'] = 'needs_frame_level_cut_detection'
    if (music_probe or {}).get('available'):
        notes['audio_notes'].append('music_file_downloaded')
    return notes


def write_analysis_md(ctx: PipelineContext, normalized: Dict[str, Any], music_meta: Dict[str, Any], raw_json_path: Path,
                      normalized_path: Path, video_path: Optional[Path], music_path: Optional[Path]) -> Path:
    creator_slug = slugify(normalized.get('author_unique_id') or normalized.get('author_name') or 'unknown-creator')
    video_id = normalized.get('video_id') or 'unknown-video'
    out_dir = ctx.storage_root / 'analysis_md' / creator_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f'{video_id}.md'

    script_shape = infer_script_shape(normalized.get('desc') or '')
    video_probe = run_ffprobe(video_path)
    music_probe = run_ffprobe(music_path)
    media_notes = infer_media_notes(video_probe, music_probe)
    lines = [
        f'# Douyin Video Analysis - {video_id}',
        '',
        '## Source',
        f'- source_input: {ctx.source_input or ""}',
        f'- endpoint_name: {ctx.endpoint_name}',
        f'- raw_json_path: {raw_json_path}',
        f'- normalized_json_path: {normalized_path}',
        f'- local_video_path: {video_path or ""}',
        f'- local_music_path: {music_path or ""}',
        f'- generated_at: {utc_now()}',
        '',
        '## Basic metadata',
        f'- video_id: {normalized.get("video_id")}',
        f'- author_name: {normalized.get("author_name")}',
        f'- author_unique_id: {normalized.get("author_unique_id")}',
        f'- create_time: {normalized.get("create_time")}',
        f'- duration_ms: {normalized.get("duration_ms")}',
        f'- digg_count: {normalized.get("digg_count")}',
        f'- comment_count: {normalized.get("comment_count")}',
        f'- share_count: {normalized.get("share_count")}',
        '',
        '## Text and script hypothesis',
        f'- desc: {normalized.get("desc") or ""}',
        f'- hook_type: {script_shape["hook_type"]}',
        f'- script_structure: {script_shape["script_structure"]}',
        '- note: this section is inferred from metadata and caption text. It is not a full semantic understanding of the video.',
        '',
        '## Media asset notes',
        f'- play_url: {normalized.get("play_url") or ""}',
        f'- music_title: {normalized.get("music_title") or music_meta.get("title") or ""}',
        f'- music_author: {normalized.get("music_author") or music_meta.get("author_name") or ""}',
        f'- music_play_url: {music_meta.get("play_url") or ""}',
        '',
        '## Video and music observations',
        f'- shot_language_guess: {media_notes["shot_language_guess"]}',
        f'- editing_rhythm_guess: {media_notes["editing_rhythm_guess"]}',
    ]
    for item in media_notes['audio_notes']:
        lines.append(f'- {item}')
    lines.extend([
        '',
        '## Production notes',
        '- Use this markdown as the primary downstream analysis source.',
        '- If a stronger video model or manual review is available, append findings here instead of rewriting from raw JSON.',
        '',
        '## Uncertainty',
        '- camera motion, shot transitions, and framing cannot be claimed with high confidence unless frame-level analysis is added.',
    ])
    md_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return md_path


def parse_mysql_dsn(dsn: str) -> Dict[str, Any]:
    parsed = urlparse(dsn)
    if parsed.scheme not in {'mysql', 'mysql+pymysql'}:
        raise ValueError('MYSQL_DSN must start with mysql:// or mysql+pymysql://')
    query = parse_qs(parsed.query)
    return {
        'host': parsed.hostname or '127.0.0.1',
        'port': parsed.port or 3306,
        'user': parsed.username,
        'password': parsed.password,
        'database': (parsed.path or '/').lstrip('/'),
        'charset': query.get('charset', ['utf8mb4'])[0],
        'autocommit': True,
    }


def get_conn(dsn: Optional[str]):
    if not dsn:
        return None
    if pymysql is None:
        raise RuntimeError('pymysql is required for MYSQL_DSN support. Install with: pip install pymysql')
    return pymysql.connect(**parse_mysql_dsn(dsn))


def upsert_creator(cur, normalized: Dict[str, Any]) -> Optional[int]:
    sec_user_id = normalized.get('author_sec_user_id')
    unique_id = normalized.get('author_unique_id')
    display_name = normalized.get('author_name')
    cur.execute(
        """
        INSERT INTO creators (sec_user_id, unique_id, display_name)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
          unique_id = VALUES(unique_id),
          display_name = VALUES(display_name),
          updated_at = CURRENT_TIMESTAMP
        """,
        (sec_user_id, unique_id, display_name),
    )
    cur.execute('SELECT id FROM creators WHERE sec_user_id = %s OR unique_id = %s LIMIT 1', (sec_user_id, unique_id))
    row = cur.fetchone()
    return row[0] if row else None


def upsert_video(cur, creator_id: Optional[int], normalized: Dict[str, Any], raw_json_path: Path, normalized_path: Path,
                 source_input: str) -> int:
    cur.execute(
        """
        INSERT INTO videos (
          aweme_id, creator_id, desc_text, duration_ms, digg_count, comment_count, collect_count,
          share_count, play_count, cover_url, play_url, source_input, raw_json_path, normalized_json_path
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          creator_id = VALUES(creator_id),
          desc_text = VALUES(desc_text),
          duration_ms = VALUES(duration_ms),
          digg_count = VALUES(digg_count),
          comment_count = VALUES(comment_count),
          collect_count = VALUES(collect_count),
          share_count = VALUES(share_count),
          play_count = VALUES(play_count),
          cover_url = VALUES(cover_url),
          play_url = VALUES(play_url),
          source_input = VALUES(source_input),
          raw_json_path = VALUES(raw_json_path),
          normalized_json_path = VALUES(normalized_json_path),
          updated_at = CURRENT_TIMESTAMP
        """,
        (
            normalized.get('video_id'), creator_id, normalized.get('desc'), normalized.get('duration_ms'),
            normalized.get('digg_count'), normalized.get('comment_count'), normalized.get('collect_count'),
            normalized.get('share_count'), normalized.get('play_count'), normalized.get('cover_url'),
            normalized.get('play_url'), source_input, str(raw_json_path), str(normalized_path)
        ),
    )
    cur.execute('SELECT id FROM videos WHERE aweme_id = %s', (normalized.get('video_id'),))
    return cur.fetchone()[0]


def upsert_music(cur, music_meta: Dict[str, Any]) -> Optional[int]:
    if not any([music_meta.get('music_id'), music_meta.get('play_url'), music_meta.get('title')]):
        return None
    key = music_meta.get('music_id') or f"url:{music_meta.get('play_url')}"
    cur.execute(
        """
        INSERT INTO music_assets (music_id, title, author_name, play_url, duration_ms)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          title = VALUES(title),
          author_name = VALUES(author_name),
          play_url = VALUES(play_url),
          duration_ms = VALUES(duration_ms),
          updated_at = CURRENT_TIMESTAMP
        """,
        (key, music_meta.get('title'), music_meta.get('author_name'), music_meta.get('play_url'), music_meta.get('duration_ms')),
    )
    cur.execute('SELECT id FROM music_assets WHERE music_id = %s', (key,))
    row = cur.fetchone()
    return row[0] if row else None


def link_video_music(cur, video_row_id: int, music_row_id: Optional[int]) -> None:
    if not music_row_id:
        return
    cur.execute('INSERT IGNORE INTO video_music_map (video_id, music_id) VALUES (%s, %s)', (video_row_id, music_row_id))


def insert_fetch_log(cur, source_type: str, source_input: str, endpoint_name: str, raw_json_path: Path, aweme_id: Optional[str]):
    cur.execute(
        """
        INSERT INTO api_fetch_logs (source_type, source_input, endpoint_name, request_params_json, response_code, raw_json_path, aweme_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (source_type, source_input, endpoint_name, json.dumps({'source_input': source_input}, ensure_ascii=False), 200, str(raw_json_path), aweme_id),
    )


def update_download_paths(cur, aweme_id: str, video_path: Optional[Path], md_path: Optional[Path]):
    cur.execute(
        """
        UPDATE videos
        SET local_video_path = %s,
            local_analysis_md_path = %s,
            download_status = %s,
            downloaded_at = CASE WHEN %s IS NOT NULL THEN CURRENT_TIMESTAMP ELSE downloaded_at END,
            analysis_status = %s,
            analyzed_at = CASE WHEN %s IS NOT NULL THEN CURRENT_TIMESTAMP ELSE analyzed_at END,
            updated_at = CURRENT_TIMESTAMP
        WHERE aweme_id = %s
        """,
        (str(video_path) if video_path else None, str(md_path) if md_path else None,
         'downloaded' if video_path else 'missing', str(video_path) if video_path else None,
         'completed' if md_path else 'pending', str(md_path) if md_path else None, aweme_id)
    )


def update_music_download(cur, music_meta: Dict[str, Any], music_path: Optional[Path]) -> None:
    if not music_meta.get('music_id') and not music_meta.get('play_url'):
        return
    key = music_meta.get('music_id') or f"url:{music_meta.get('play_url')}"
    cur.execute(
        """
        UPDATE music_assets
        SET local_music_path = %s,
            download_status = %s,
            downloaded_at = CASE WHEN %s IS NOT NULL THEN CURRENT_TIMESTAMP ELSE downloaded_at END,
            updated_at = CURRENT_TIMESTAMP
        WHERE music_id = %s
        """,
        (str(music_path) if music_path else None, 'downloaded' if music_path else 'missing', str(music_path) if music_path else None, key),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('raw_payload_json')
    parser.add_argument('--storage-root', default=os.getenv('DOUYIN_STORAGE_ROOT', './storage'))
    parser.add_argument('--mysql-dsn', default=os.getenv('MYSQL_DSN'))
    parser.add_argument('--endpoint-name', default='fetch_one_video_v2')
    parser.add_argument('--source-input', default='')
    args = parser.parse_args()

    ctx = PipelineContext(
        storage_root=Path(args.storage_root).resolve(),
        mysql_dsn=args.mysql_dsn,
        endpoint_name=args.endpoint_name,
        source_input=args.source_input,
    )
    payload = load_json(Path(args.raw_payload_json))
    normalized = normalize_single_video(payload, source_input=args.source_input)
    video_id = normalized.get('video_id') or 'unknown-video'
    creator_slug = slugify(normalized.get('author_unique_id') or normalized.get('author_name') or 'unknown-creator')
    music_meta = extract_music_meta(payload)

    raw_json_path = save_raw_payload(payload, ctx, video_id)
    normalized_path = save_normalized(normalized, ctx, video_id)

    video_path = None
    if normalized.get('play_url'):
        video_path = download_asset(normalized.get('play_url'), ctx.storage_root / 'downloads' / 'videos' / creator_slug / str(video_id))
    music_path = None
    if music_meta.get('play_url'):
        music_key = slugify(str(music_meta.get('music_id') or music_meta.get('title') or video_id))
        music_path = download_asset(music_meta.get('play_url'), ctx.storage_root / 'downloads' / 'music' / creator_slug / music_key)

    md_path = write_analysis_md(ctx, normalized, music_meta, raw_json_path, normalized_path, video_path, music_path)

    conn = get_conn(ctx.mysql_dsn)
    if conn:
        with conn.cursor() as cur:
            creator_id = upsert_creator(cur, normalized)
            video_row_id = upsert_video(cur, creator_id, normalized, raw_json_path, normalized_path, ctx.source_input)
            music_row_id = upsert_music(cur, music_meta)
            link_video_music(cur, video_row_id, music_row_id)
            insert_fetch_log(cur, 'douyin_single_video', ctx.source_input, ctx.endpoint_name, raw_json_path, normalized.get('video_id'))
            update_download_paths(cur, normalized.get('video_id'), video_path, md_path)
            update_music_download(cur, music_meta, music_path)
        conn.close()

    result = {
        'video_id': normalized.get('video_id'),
        'raw_json_path': str(raw_json_path),
        'normalized_json_path': str(normalized_path),
        'local_video_path': str(video_path) if video_path else None,
        'local_music_path': str(music_path) if music_path else None,
        'local_analysis_md_path': str(md_path),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
