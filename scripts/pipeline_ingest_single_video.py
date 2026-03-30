#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    import pymysql  # type: ignore
except Exception:
    pymysql = None

from normalize_single_video import normalize_single_video

SCRIPT_DIR = Path(__file__).resolve().parent
import sys
PACK_ROOT = SCRIPT_DIR.parent
if str(PACK_ROOT) not in sys.path:
    sys.path.insert(0, str(PACK_ROOT))

from common.storage import get_creators_root

CREATORS_ROOT = get_creators_root()
ANALYSIS_SCRIPT = PACK_ROOT / 'tools' / 'analyze-local-video' / 'scripts' / 'run.py'


@dataclass
class PipelineContext:
    creators_root: Path
    mysql_dsn: Optional[str]
    endpoint_name: str
    source_input: str
    run_analysis: bool


def slugify(value: str) -> str:
    value = (value or 'unknown').strip().lower()
    value = re.sub(r'[^a-z0-9一-鿿_-]+', '-', value)
    value = re.sub(r'-+', '-', value).strip('-')
    return value or 'unknown'


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


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
        ext = Path(urlparse(url).path).suffix
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
    out = creator_root(ctx, normalized) / 'raw_api' / 'douyin_single_video' / today_dir()
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{normalized.get('video_id') or 'unknown-video'}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def save_normalized(normalized: Dict[str, Any], ctx: PipelineContext) -> Path:
    out = creator_root(ctx, normalized) / 'normalized' / 'douyin_single_video'
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{normalized.get('video_id') or 'unknown-video'}.json"
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def download_asset(url: Optional[str], path: Path) -> tuple[Optional[Path], Optional[str]]:
    if not url:
        return None, 'missing_url'
    path.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urlopen(req, timeout=120) as resp:
            content_type = resp.headers.get('Content-Type')
            if path.suffix == '':
                path = path.with_suffix(choose_extension(url, content_type, '.bin'))
            with open(path, 'wb') as f:
                shutil.copyfileobj(resp, f)
        return path, None
    except Exception as exc:
        return None, str(exc)


def parse_mysql_dsn(dsn: str) -> Dict[str, Any]:
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(dsn)
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


def parse_create_time(value: Any):
    from datetime import datetime
    if value in (None, ''):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(int(value))
        except Exception:
            return None
    raw = str(value).strip()
    if raw.isdigit():
        try:
            return datetime.fromtimestamp(int(raw))
        except Exception:
            return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(raw[:19], fmt)
        except Exception:
            continue
    return None


def get_or_create_creator_id(cur, normalized: Dict[str, Any]) -> Optional[int]:
    sec_user_id = normalized.get('author_sec_user_id')
    unique_id = normalized.get('author_unique_id')
    display_name = normalized.get('author_name')
    if sec_user_id:
        cur.execute(
            """
            INSERT INTO creators (sec_user_id, unique_id, display_name)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
              unique_id = COALESCE(VALUES(unique_id), unique_id),
              display_name = COALESCE(VALUES(display_name), display_name)
            """,
            (sec_user_id, unique_id, display_name),
        )
        cur.execute('SELECT id FROM creators WHERE sec_user_id = %s', (sec_user_id,))
        row = cur.fetchone()
        return row[0] if row else None
    if unique_id:
        cur.execute('SELECT id FROM creators WHERE unique_id = %s LIMIT 1', (unique_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute('INSERT INTO creators (unique_id, display_name) VALUES (%s, %s)', (unique_id, display_name))
        return cur.lastrowid
    return None


def get_or_create_music_asset_id(cur, music_meta: Dict[str, Any], music_path: Optional[Path], music_download_status: str) -> Optional[int]:
    music_id = str(music_meta.get('music_id') or '') if music_meta.get('music_id') else None
    if not (music_id or music_meta.get('play_url')):
        return None
    if music_id:
        cur.execute(
            """
            INSERT INTO music_assets (music_id, title, author_name, play_url, duration_ms, local_music_path, download_status, downloaded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              title = COALESCE(VALUES(title), title),
              author_name = COALESCE(VALUES(author_name), author_name),
              play_url = COALESCE(VALUES(play_url), play_url),
              duration_ms = COALESCE(VALUES(duration_ms), duration_ms),
              local_music_path = COALESCE(VALUES(local_music_path), local_music_path),
              download_status = VALUES(download_status),
              downloaded_at = COALESCE(VALUES(downloaded_at), downloaded_at)
            """,
            (
                music_id,
                music_meta.get('title'),
                music_meta.get('author_name'),
                music_meta.get('play_url'),
                music_meta.get('duration_ms'),
                str(music_path) if music_path else None,
                music_download_status,
                datetime.now() if music_path else None,
            ),
        )
        cur.execute('SELECT id FROM music_assets WHERE music_id = %s', (music_id,))
        row = cur.fetchone()
        return row[0] if row else None
    return None


def upsert_mysql(ctx: PipelineContext, normalized: Dict[str, Any], music_meta: Dict[str, Any], raw_json_path: Path,
                 normalized_path: Path, video_path: Optional[Path], music_path: Optional[Path],
                 download_status: str, analysis_status: str, md_path: Optional[Path], music_download_status: str) -> None:
    conn = with_mysql(ctx)
    if conn is None:
        return
    video_id = str(normalized.get('video_id') or '')
    with conn.cursor() as cur:
        creator_id = get_or_create_creator_id(cur, normalized)
        create_time = parse_create_time(normalized.get('create_time'))
        cur.execute(
            """
            INSERT INTO videos (
              aweme_id, creator_id, desc_text, create_time, duration_ms,
              digg_count, comment_count, collect_count, share_count, play_count,
              cover_url, play_url, source_input, raw_json_path, normalized_json_path,
              local_video_path, local_analysis_md_path, download_status, analysis_status,
              downloaded_at, analyzed_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              creator_id = VALUES(creator_id),
              desc_text = VALUES(desc_text),
              create_time = VALUES(create_time),
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
              local_video_path = VALUES(local_video_path),
              local_analysis_md_path = VALUES(local_analysis_md_path),
              download_status = VALUES(download_status),
              analysis_status = VALUES(analysis_status),
              downloaded_at = COALESCE(VALUES(downloaded_at), downloaded_at),
              analyzed_at = COALESCE(VALUES(analyzed_at), analyzed_at)
            """,
            (
                video_id,
                creator_id,
                normalized.get('desc'),
                create_time,
                normalized.get('duration_ms'),
                normalized.get('digg_count'),
                normalized.get('comment_count'),
                normalized.get('collect_count'),
                normalized.get('share_count'),
                normalized.get('play_count'),
                normalized.get('cover_url'),
                normalized.get('play_url'),
                ctx.source_input,
                str(raw_json_path),
                str(normalized_path),
                str(video_path) if video_path else None,
                str(md_path) if md_path else None,
                download_status,
                analysis_status,
                datetime.now() if video_path else None,
                datetime.now() if md_path else None,
            ),
        )
        music_asset_id = get_or_create_music_asset_id(cur, music_meta, music_path, music_download_status)
        if music_asset_id:
            cur.execute('SELECT id FROM videos WHERE aweme_id = %s', (video_id,))
            video_row = cur.fetchone()
            if video_row:
                cur.execute(
                    """
                    INSERT INTO video_music_map (video_id, music_id)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE music_id = VALUES(music_id)
                    """,
                    (video_row[0], music_asset_id),
                )
        cur.execute(
            """
            INSERT INTO api_fetch_logs (source_type, source_input, endpoint_name, raw_json_path, aweme_id, fetched_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            ('douyin_single_video', ctx.source_input, ctx.endpoint_name, str(raw_json_path), video_id),
        )
    conn.close()


def maybe_run_analysis(normalized_path: Path, mysql_dsn: Optional[str]) -> tuple[Optional[Path], str, Dict[str, Any]]:
    if not ANALYSIS_SCRIPT.exists():
        return None, 'pending', {'ok': False, 'reason': 'analysis_script_missing'}
    cmd = [sys.executable, str(ANALYSIS_SCRIPT), str(normalized_path)]
    if mysql_dsn:
        cmd.extend(['--mysql-dsn', mysql_dsn])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    payload: Dict[str, Any] = {}
    try:
        payload = json.loads((proc.stdout or '').strip() or '{}')
    except Exception:
        payload = {'ok': False, 'reason': 'analysis_output_not_json', 'stdout': proc.stdout, 'stderr': proc.stderr}
    if proc.returncode == 0 and payload.get('ok'):
        md = payload.get('analysis_md_path')
        return Path(md).expanduser().resolve() if md else None, 'completed', payload
    if payload.get('reason') == 'video_not_downloaded':
        return None, 'blocked_missing_video', payload
    return None, 'failed', payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input_json')
    parser.add_argument('--mysql-dsn', default=os.getenv('MYSQL_DSN'))
    parser.add_argument('--endpoint-name', default='fetch_one_video_v2')
    parser.add_argument('--source-input', default='')
    parser.add_argument('--run-analysis', action='store_true', help='Run deep per-video analysis only after successful local video download.')
    args = parser.parse_args()

    payload = load_json(Path(args.input_json))
    normalized = normalize_single_video(payload, source_input=args.source_input)
    ctx = PipelineContext(
        creators_root=CREATORS_ROOT.resolve(),
        mysql_dsn=args.mysql_dsn,
        endpoint_name=args.endpoint_name,
        source_input=args.source_input,
        run_analysis=bool(args.run_analysis),
    )

    raw_json_path = save_raw_payload(payload, ctx, normalized)
    normalized_path = save_normalized(normalized, ctx)
    music_meta = extract_music_meta(payload)

    creator_dir = creator_root(ctx, normalized)
    downloads_dir = creator_dir / 'downloads'
    video_id = normalized.get('video_id') or 'unknown-video'
    creator_slug = get_creator_slug(normalized)

    video_path, video_error = download_asset(normalized.get('play_url'), downloads_dir / 'videos' / str(video_id))
    download_status = 'downloaded' if video_path else 'failed'

    music_key = slugify(str(music_meta.get('music_id') or music_meta.get('title') or f'{creator_slug}-music'))
    music_path, music_error = download_asset(music_meta.get('play_url'), downloads_dir / 'music' / music_key) if music_meta.get('play_url') else (None, 'missing_url')
    music_download_status = 'downloaded' if music_path else ('missing_url' if music_error == 'missing_url' else 'failed')

    md_path: Optional[Path] = None
    analysis_status = 'pending' if video_path else 'blocked_missing_video'
    analysis_result: Dict[str, Any] = {'ok': False, 'reason': 'analysis_not_requested'}
    if ctx.run_analysis and video_path:
        md_path, analysis_status, analysis_result = maybe_run_analysis(normalized_path, ctx.mysql_dsn)
    elif ctx.run_analysis and not video_path:
        analysis_status = 'blocked_missing_video'
        analysis_result = {'ok': False, 'reason': 'video_not_downloaded'}

    upsert_mysql(ctx, normalized, music_meta, raw_json_path, normalized_path, video_path, music_path,
                 download_status, analysis_status, md_path, music_download_status)

    print(json.dumps({
        'creator_root': str(creator_dir),
        'raw_json_path': str(raw_json_path),
        'normalized_json_path': str(normalized_path),
        'local_video_path': str(video_path) if video_path else None,
        'local_music_path': str(music_path) if music_path else None,
        'download_status': download_status,
        'video_download_error': video_error,
        'music_download_status': music_download_status,
        'music_download_error': music_error,
        'analysis_status': analysis_status,
        'markdown_analysis_path': str(md_path) if md_path else None,
        'analysis_result': analysis_result,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
