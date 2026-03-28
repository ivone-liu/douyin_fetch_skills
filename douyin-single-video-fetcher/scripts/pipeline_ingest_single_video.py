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
- no repo-local storage root is required
- data is written under ~/.openclaw/workspace/data/creators/<creator-slug>/...
- OPENCLAW_WORKSPACE_DATA_ROOT can override the root when needed

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
from typing import Any, Dict, Iterable, Optional, List
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    import pymysql  # type: ignore
except Exception:
    pymysql = None

from fetch_single_video import normalize_single_video

SKILL_DIR = Path(__file__).resolve().parents[1]
import sys
PACK_ROOT = SKILL_DIR.parent
if str(PACK_ROOT) not in sys.path:
    sys.path.insert(0, str(PACK_ROOT))

from common.storage import get_creators_root

CREATORS_ROOT = get_creators_root()


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
    elif any(x in desc for x in ['3个', '5个', '10个', '步骤', '方法', '公式']):
        hook = 'promise_hook'
    elif any(x in desc for x in ['我发现', '以前', '后来', '直到']):
        hook = 'story_hook'
    elif len(desc) <= 12:
        hook = 'direct_statement'
    else:
        hook = 'statement_hook'

    if any(x in desc for x in ['教程', '步骤', '方法', '怎么做']):
        structure = 'problem -> steps -> result -> cta'
        archetype = 'educational'
    elif any(x in desc for x in ['对比', '区别', '哪个好', '测评']):
        structure = 'problem -> comparison -> verdict -> cta'
        archetype = 'comparison'
    elif any(x in desc for x in ['我发现', '以前', '后来', '踩坑']):
        structure = 'story -> realization -> lesson -> cta'
        archetype = 'story'
    elif any(x in desc for x in ['清单', '合集', '盘点', '推荐']):
        structure = 'hook -> list -> takeaway -> cta'
        archetype = 'listicle'
    else:
        structure = 'problem -> explanation -> action -> cta'
        archetype = 'unknown'
    return {'hook_type': hook, 'script_structure': structure, 'content_archetype': archetype}


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


def build_structured_analysis(normalized: Dict[str, Any], script_shape: Dict[str, Any], media_notes: Dict[str, Any]) -> Dict[str, Any]:
    desc = normalized.get('desc') or ''
    beats: List[Dict[str, Any]] = [
        {
            'beat_id': 1,
            'beat_type': 'hook',
            'purpose': 'Open with the caption-level promise or problem.',
            'time_range': 'unknown',
            'summary': desc[:40] if desc else 'Caption-level hook placeholder',
            'proof_type': 'unknown',
        },
        {
            'beat_id': 2,
            'beat_type': 'delivery',
            'purpose': 'Explain the core claim, method, or comparison.',
            'time_range': 'unknown',
            'summary': script_shape['script_structure'],
            'proof_type': 'claim',
        },
        {
            'beat_id': 3,
            'beat_type': 'cta',
            'purpose': 'End with an interaction or conversion action if present.',
            'time_range': 'unknown',
            'summary': 'CTA placeholder pending transcript or manual review.',
            'proof_type': 'unknown',
        },
    ]
    return {
        'analysis_version': '1.0.0',
        'video': {
            'video_id': normalized.get('video_id'),
            'author_name': normalized.get('author_name'),
            'author_unique_id': normalized.get('author_unique_id'),
            'author_sec_user_id': normalized.get('author_sec_user_id'),
            'create_time': normalized.get('create_time'),
            'duration_ms': normalized.get('duration_ms'),
            'desc': desc,
        },
        'analysis_scope': {
            'source_depth': 'caption_plus_media_probe',
            'confidence': 'low',
            'notes': [
                'This is a structured scaffold derived from caption text and media probes, not a full direct video reading.',
                'Beat timing, shot details, and dialogue tactics require transcript, frame review, or manual annotation for high confidence.',
            ],
        },
        'positioning': {
            'primary_goal': 'unknown',
            'secondary_goals': [],
            'content_archetype': script_shape['content_archetype'],
            'sub_archetypes': [],
            'target_audience': 'unknown',
        },
        'hook': {
            'hook_type': script_shape['hook_type'],
            'hook_text': desc[:80],
            'visual_hook': media_notes['shot_language_guess'],
            'emotion': 'unknown',
            'promise': desc[:80],
            'time_range': 'unknown',
        },
        'narrative': {
            'structure_formula': script_shape['script_structure'],
            'beats': beats,
        },
        'shot_plan': {
            'dominant_style': media_notes['shot_language_guess'],
            'shots': [
                {
                    'shot_id': 1,
                    'beat_id': 1,
                    'time_range': 'unknown',
                    'shot_size': 'unknown',
                    'camera_angle': 'unknown',
                    'camera_movement': 'unknown',
                    'subject': 'unknown',
                    'scene_task': 'hook_delivery',
                    'transition_in': 'unknown',
                    'transition_out': 'unknown',
                    'confidence': 'low',
                }
            ],
        },
        'dialogue': {
            'delivery_style': 'unknown',
            'structure': script_shape['script_structure'],
            'rhetorical_moves': [],
            'cta_type': 'unknown',
        },
        'editing_packaging': {
            'pace': 'unknown',
            'subtitle_style': 'unknown',
            'transition_types': [],
            'packaging_elements': [],
            'audio_strategy': 'music_file_downloaded' if 'music_file_downloaded' in media_notes['audio_notes'] else 'unknown',
        },
        'persuasion': {
            'emotion_triggers': [],
            'credibility_signals': [],
            'conversion_devices': [],
        },
        'reusable_patterns': {
            'opening_formula': desc[:80],
            'structure_formula': script_shape['script_structure'],
            'shot_formula': media_notes['shot_language_guess'],
            'dialogue_formula': '',
            'applicable_scenarios': [],
            'not_applicable_scenarios': ['Do not treat this scaffold as frame-level truth without manual review.'],
        },
        'risks_and_limits': {
            'risk_flags': ['scaffold_only'],
            'unknowns': [
                'exact beat timing unknown',
                'shot size and camera movement unknown',
                'dialogue tactics unknown',
            ],
        },
    }


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
    structured = build_structured_analysis(normalized, script_shape, media_notes)
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
        f'- content_archetype: {script_shape["content_archetype"]}',
        '- note: this section is a structured scaffold inferred from caption text and media probes. It is not a frame-level semantic read of the video.',
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
        '## Structured analysis JSON',
        '```json',
        json.dumps(structured, ensure_ascii=False, indent=2),
        '```',
        '',
        '## Production notes',
        '- This markdown file is the preferred downstream analysis source.',
        '- Read the structured JSON block first when building KB entries or generating scripts.',
        '- If deeper visual or audio analysis is needed, enrich this file rather than re-reading raw API payloads each time.',
        '',
        '## Uncertainty',
        '- Shot language and editing rhythm remain low-confidence until frame-level analysis or manual review is added.',
        '- TikHub metadata alone cannot prove camera motion, cut timing, or rhetorical delivery.',
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


def parse_create_time(value: Any) -> Optional[datetime]:
    if value in (None, ''):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(int(value))
        except Exception:
            return None
    if isinstance(value, str):
        raw = value.strip()
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
            cur.execute('UPDATE creators SET display_name = COALESCE(%s, display_name) WHERE id = %s', (display_name, row[0]))
            return row[0]
        cur.execute(
            'INSERT INTO creators (unique_id, display_name) VALUES (%s, %s)',
            (unique_id, display_name),
        )
        return cur.lastrowid
    if display_name:
        cur.execute('INSERT INTO creators (display_name) VALUES (%s)', (display_name,))
        return cur.lastrowid
    return None


def get_or_create_music_asset_id(cur, music_meta: Dict[str, Any], music_path: Optional[Path]) -> Optional[int]:
    music_id = str(music_meta.get('music_id') or '') if music_meta.get('music_id') else None
    play_url = music_meta.get('play_url')
    title = music_meta.get('title')
    author_name = music_meta.get('author_name')
    duration_ms = music_meta.get('duration_ms')
    if not (music_id or play_url):
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
            (music_id, title, author_name, play_url, duration_ms, str(music_path) if music_path else None, 'downloaded' if music_path else 'pending', datetime.now() if music_path else None),
        )
        cur.execute('SELECT id FROM music_assets WHERE music_id = %s', (music_id,))
        row = cur.fetchone()
        return row[0] if row else None
    cur.execute(
        'INSERT INTO music_assets (title, author_name, play_url, duration_ms, local_music_path, download_status, downloaded_at) VALUES (%s, %s, %s, %s, %s, %s, %s)',
        (title, author_name, play_url, duration_ms, str(music_path) if music_path else None, 'downloaded' if music_path else 'pending', datetime.now() if music_path else None),
    )
    return cur.lastrowid


def upsert_mysql(ctx: PipelineContext, normalized: Dict[str, Any], music_meta: Dict[str, Any], raw_json_path: Path,
                 normalized_path: Path, video_path: Optional[Path], music_path: Optional[Path], md_path: Path) -> None:
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
              downloaded_at = VALUES(downloaded_at),
              analyzed_at = VALUES(analyzed_at)
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
                str(md_path),
                'downloaded' if video_path else 'pending',
                'completed',
                datetime.now() if video_path else None,
                datetime.now(),
            ),
        )
        music_asset_id = get_or_create_music_asset_id(cur, music_meta, music_path)
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
