#!/usr/bin/env python3
"""End-to-end single-video ingestion pipeline.

What it does:
1. read a raw TikHub single-video payload
2. save raw payload to a skill-pack-local creator directory
3. normalize key fields
4. upsert searchable fields into MySQL
5. download video and music into creator-grouped local directories
6. generate one markdown analysis file per video
7. update MySQL with local paths and statuses

Default storage behavior:
- no external storage root is required
- data is written inside this skill pack under ../data/creators/<creator-slug>/...
- this makes the storage contract deterministic across installs

Example:
python scripts/pipeline_ingest_single_video.py raw_payload.json   --mysql-dsn 'mysql://user:pass@127.0.0.1:3306/openclaw_douyin?charset=utf8mb4'   --endpoint-name fetch_one_video_v2   --source-input 'https://v.douyin.com/xxxx/'
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
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    import pymysql  # type: ignore
except Exception:
    pymysql = None

from fetch_single_video import normalize_single_video

SKILL_DIR = Path(__file__).resolve().parents[1]
PACK_ROOT = SKILL_DIR.parent
DATA_ROOT = PACK_ROOT / 'data'
CREATORS_ROOT = DATA_ROOT / 'creators'


@dataclass
class PipelineContext:
    creators_root: Path
    mysql_dsn: Optional[str]
    endpoint_name: str
    source_input: str


def slugify(value: str) -> str:
    value = (value or 'unknown').strip().lower()
    value = re.sub(r'[^a-z0-9一-鿿_-]+', '-', value)
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


def get_creator_slug(normalized: Dict[str, Any]) -> str:
    return slugify(normalized.get('author_unique_id') or normalized.get('author_name') or 'unknown-creator')


def creator_root(ctx: PipelineContext, normalized: Dict[str, Any]) -> Path:
    root = ctx.creators_root / get_creator_slug(normalized)
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_raw_payload(payload: Dict[str, Any], ctx: PipelineContext, normalized: Dict[str, Any]) -> Path:
    video_id = normalized.get('video_id') or 'unknown-video'
    out = creator_root(ctx, normalized) / 'raw_api' / 'douyin_single_video' / today_dir()
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'{video_id}.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def save_normalized(normalized: Dict[str, Any], ctx: PipelineContext) -> Path:
    video_id = normalized.get('video_id') or 'unknown-video'
    out = creator_root(ctx, normalized) / 'normalized' / 'douyin_single_video'
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
    creator_dir = creator_root(ctx, normalized)
    video_id = normalized.get('video_id') or 'unknown-video'
    out_dir = creator_dir / 'analysis_md'
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
        '- This markdown file is the preferred downstream analysis source.',
        '- Read this file first when building KB entries or generating scripts.',
        '- If deeper visual or audio analysis is needed, extend this file rather than re-reading raw API payloads each time.',
        '',
        '## Uncertainty',
        '- Shot language and editing rhythm remain low-confidence until frame-level analysis or manual review is added.',
        '- TikHub metadata alone cannot prove camera motion or cut timing.',
    ])
    md_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return md_path


def parse_mysql_dsn(dsn: str) -> Dict[str, Any]:
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(dsn)
    if parsed.scheme not in {'mysql'}:
        raise ValueError('MYSQL_DSN must start with mysql://')
    qs = parse_qs(parsed.query)
    return {
        'host': parsed.hostname or '127.0.0.1',
        'port': parsed.port or 3306,
        'user': parsed.username,
        'password': parsed.password,
        'database': (parsed.path or '/').lstrip('/'),
        'charset': qs.get('charset', ['utf8mb4'])[0],
        'autocommit': True,
    }


def with_mysql(ctx: PipelineContext):
    if not ctx.mysql_dsn:
        return None
    if pymysql is None:
        raise RuntimeError('pymysql is required when MYSQL_DSN is provided')
    return pymysql.connect(**parse_mysql_dsn(ctx.mysql_dsn))


def upsert_mysql(ctx: PipelineContext, normalized: Dict[str, Any], music_meta: Dict[str, Any], raw_json_path: Path,
                 normalized_path: Path, video_path: Optional[Path], music_path: Optional[Path], md_path: Path) -> None:
    conn = with_mysql(ctx)
    if conn is None:
        return
    creator_slug = get_creator_slug(normalized)
    video_id = str(normalized.get('video_id') or '')
    music_id = str(music_meta.get('music_id') or '') if music_meta.get('music_id') else None
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO creators (creator_slug, unique_id, sec_user_id, display_name, last_seen_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
              unique_id = VALUES(unique_id),
              sec_user_id = VALUES(sec_user_id),
              display_name = VALUES(display_name),
              last_seen_at = NOW()
            """,
            (creator_slug, normalized.get('author_unique_id'), normalized.get('author_sec_user_id'), normalized.get('author_name')),
        )
        cur.execute(
            """
            INSERT INTO videos (
              aweme_id, creator_slug, desc_text, create_time_raw, duration_ms,
              play_url, cover_url, raw_json_path, normalized_json_path,
              local_video_path, markdown_analysis_path, download_status, analysis_status,
              digg_count, comment_count, share_count, collect_count, play_count, last_ingested_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
              desc_text = VALUES(desc_text),
              create_time_raw = VALUES(create_time_raw),
              duration_ms = VALUES(duration_ms),
              play_url = VALUES(play_url),
              cover_url = VALUES(cover_url),
              raw_json_path = VALUES(raw_json_path),
              normalized_json_path = VALUES(normalized_json_path),
              local_video_path = VALUES(local_video_path),
              markdown_analysis_path = VALUES(markdown_analysis_path),
              download_status = VALUES(download_status),
              analysis_status = VALUES(analysis_status),
              digg_count = VALUES(digg_count),
              comment_count = VALUES(comment_count),
              share_count = VALUES(share_count),
              collect_count = VALUES(collect_count),
              play_count = VALUES(play_count),
              last_ingested_at = NOW()
            """,
            (
                video_id, creator_slug, normalized.get('desc'), str(normalized.get('create_time') or ''), normalized.get('duration_ms'),
                normalized.get('play_url'), normalized.get('cover_url'), str(raw_json_path), str(normalized_path),
                str(video_path) if video_path else None, str(md_path),
                'downloaded' if video_path else 'missing_video', 'completed',
                normalized.get('digg_count'), normalized.get('comment_count'), normalized.get('share_count'),
                normalized.get('collect_count'), normalized.get('play_count'),
            ),
        )
        if music_id or music_meta.get('play_url'):
            cur.execute(
                """
                INSERT INTO music_assets (music_id, title, author_name, duration_ms, play_url, local_music_path, download_status, last_seen_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                  title = VALUES(title),
                  author_name = VALUES(author_name),
                  duration_ms = VALUES(duration_ms),
                  play_url = VALUES(play_url),
                  local_music_path = VALUES(local_music_path),
                  download_status = VALUES(download_status),
                  last_seen_at = NOW()
                """,
                (
                    music_id or f'music-url::{music_meta.get("play_url")}', music_meta.get('title'), music_meta.get('author_name'),
                    music_meta.get('duration_ms'), music_meta.get('play_url'), str(music_path) if music_path else None,
                    'downloaded' if music_path else 'missing_music_url',
                ),
            )
            cur.execute(
                """
                INSERT INTO video_music_map (aweme_id, music_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE music_id = VALUES(music_id)
                """,
                (video_id, music_id or f'music-url::{music_meta.get("play_url")}'),
            )
        cur.execute(
            """
            INSERT INTO api_fetch_logs (aweme_id, endpoint_name, source_input, raw_json_path, fetched_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (video_id, ctx.endpoint_name, ctx.source_input, str(raw_json_path)),
        )
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input_json')
    parser.add_argument('--mysql-dsn', default=os.getenv('MYSQL_DSN'))
    parser.add_argument('--endpoint-name', default='fetch_one_video_v2')
    parser.add_argument('--source-input', default='')
    args = parser.parse_args()

    payload = load_json(Path(args.input_json))
    normalized = normalize_single_video(payload, source_input=args.source_input)
    ctx = PipelineContext(
        creators_root=CREATORS_ROOT.resolve(),
        mysql_dsn=args.mysql_dsn,
        endpoint_name=args.endpoint_name,
        source_input=args.source_input,
    )

    raw_json_path = save_raw_payload(payload, ctx, normalized)
    normalized_path = save_normalized(normalized, ctx)
    music_meta = extract_music_meta(payload)

    creator_dir = creator_root(ctx, normalized)
    downloads_dir = creator_dir / 'downloads'
    video_id = normalized.get('video_id') or 'unknown-video'
    creator_slug = get_creator_slug(normalized)

    video_path = None
    if normalized.get('play_url'):
        video_path = download_asset(normalized.get('play_url'), downloads_dir / 'videos' / str(video_id))

    music_path = None
    music_key = slugify(str(music_meta.get('music_id') or music_meta.get('title') or f'{creator_slug}-music'))
    if music_meta.get('play_url'):
        music_path = download_asset(music_meta.get('play_url'), downloads_dir / 'music' / music_key)

    md_path = write_analysis_md(ctx, normalized, music_meta, raw_json_path, normalized_path, video_path, music_path)
    upsert_mysql(ctx, normalized, music_meta, raw_json_path, normalized_path, video_path, music_path, md_path)

    print(json.dumps({
        'creator_root': str(creator_dir),
        'raw_json_path': str(raw_json_path),
        'normalized_json_path': str(normalized_path),
        'local_video_path': str(video_path) if video_path else None,
        'local_music_path': str(music_path) if music_path else None,
        'markdown_analysis_path': str(md_path),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
