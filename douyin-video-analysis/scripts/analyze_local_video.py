#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PACK_ROOT = Path(__file__).resolve().parents[2]
if str(PACK_ROOT) not in sys.path:
    sys.path.insert(0, str(PACK_ROOT))

from common.storage import creator_root, detect_creator_slug_from_path, slugify
from common.video_analysis import (
    build_contact_sheet,
    choose_sample_timestamps,
    classify_editing_pace,
    detect_copy_patterns,
    detect_scene_changes,
    engagement_profile,
    extract_hashtags,
    extract_keyframes,
    extract_media_profile,
    ffprobe_json,
)

try:
    import pymysql  # type: ignore
except Exception:
    pymysql = None


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def with_mysql(dsn: Optional[str]):
    if not dsn:
        return None
    if pymysql is None:
        raise RuntimeError('pymysql is required when MYSQL_DSN is provided')
    return pymysql.connect(**parse_mysql_dsn(dsn))


def find_video_file(normalized_path: Path, normalized: Dict[str, Any]) -> Optional[Path]:
    video_id = str(normalized.get('video_id') or normalized_path.stem)
    creator_slug = detect_creator_slug_from_path(normalized_path) or slugify(normalized.get('author_unique_id') or normalized.get('author_name') or 'unknown-creator')
    root = creator_root(creator_slug)
    video_dir = root / 'downloads' / 'videos'
    if not video_dir.exists():
        return None
    exact = list(video_dir.glob(f'{video_id}.*'))
    if exact:
        return exact[0]
    fallback = sorted(video_dir.glob(f'{video_id}*'))
    return fallback[0] if fallback else None


def infer_primary_goal(ep: Dict[str, Any]) -> str:
    share_ratio = ep.get('share_like_ratio') or 0
    collect_ratio = ep.get('collect_like_ratio') or 0
    comment_ratio = ep.get('comment_like_ratio') or 0
    if share_ratio >= 0.08 or comment_ratio >= 0.03:
        return 'engagement'
    if collect_ratio >= 0.12:
        return 'trust'
    return 'awareness'


def infer_archetype(desc: str, hashtags: List[str], duration_sec: Optional[float]) -> str:
    text = desc or ''
    tags_text = ' '.join(hashtags)
    if any(x in text for x in ['测评', '对比', '哪个好', '区别']):
        return 'comparison'
    if any(x in text for x in ['教程', '步骤', '方法', '怎么做']):
        return 'educational'
    if any(x in text for x in ['我发现', '以前', '后来', '直到', '那天']):
        return 'story'
    if 'vlog' in text.lower() or 'vlog' in tags_text.lower():
        return 'vlog'
    if duration_sec and duration_sec <= 20:
        return 'showcase'
    return 'unknown'


def infer_hook(desc: str, copy_signals: List[str]) -> Dict[str, str]:
    text = desc or ''
    if 'inner_conflict' in copy_signals:
        return {
            'hook_type': 'conflict_hook',
            'emotion': '矛盾与暧昧',
            'promise': '利用情绪矛盾引发停留和代入',
        }
    if 'question' in copy_signals:
        return {
            'hook_type': 'question_hook',
            'emotion': '好奇',
            'promise': '用问题制造停留',
        }
    if 'story_turn' in copy_signals:
        return {
            'hook_type': 'story_hook',
            'emotion': '转折',
            'promise': '用经历转折吸引继续观看',
        }
    if len(text) <= 20:
        return {
            'hook_type': 'direct_statement',
            'emotion': '直给',
            'promise': '短句直接进入状态',
        }
    return {
        'hook_type': 'unknown',
        'emotion': 'unknown',
        'promise': 'unknown',
    }


def beat_ranges(duration_sec: Optional[float]) -> List[tuple[str, str]]:
    if not duration_sec or duration_sec <= 0:
        return [('0.0-unknown', 'unknown')]
    d = duration_sec
    points = [0.0, d * 0.18, d * 0.45, d * 0.78, d]
    ranges = []
    labels = ['hook', 'setup', 'delivery', 'payoff']
    for i, label in enumerate(labels):
        start = round(points[i], 2)
        end = round(points[i + 1], 2)
        ranges.append((f'{start}-{end}', label))
    return ranges


def build_structured_analysis(normalized: Dict[str, Any], video_path: Path, media_profile: Dict[str, Any],
                              scene_info: Dict[str, Any], keyframe_paths: List[Path], contact_sheet: Optional[Path]) -> Dict[str, Any]:
    desc = normalized.get('desc') or ''
    copy_profile = detect_copy_patterns(desc)
    ep = engagement_profile(normalized)
    duration_sec = media_profile.get('duration_sec')
    pace_info = classify_editing_pace(duration_sec, len(scene_info.get('scene_times') or []))
    archetype = infer_archetype(desc, copy_profile['hashtags'], duration_sec)
    hook = infer_hook(desc, copy_profile['signals'])
    goal = infer_primary_goal(ep)

    beats = []
    for idx, (time_range, label) in enumerate(beat_ranges(duration_sec), start=1):
        purpose_map = {
            'hook': '在极短时间内建立情绪、关系或反差。',
            'setup': '补足场景，让观众理解这条视频在说什么。',
            'delivery': '推进主要内容或情绪表达。',
            'payoff': '给出余味、停顿或互动出口。',
        }
        proof_map = {
            'hook': 'claim',
            'setup': 'story',
            'delivery': 'demo',
            'payoff': 'story',
        }
        beats.append({
            'beat_id': idx,
            'beat_type': label,
            'purpose': purpose_map.get(label, 'unknown'),
            'time_range': time_range,
            'summary': '基于时长和画面节奏的分段，具体内容仍需结合关键帧复核。',
            'proof_type': proof_map.get(label, 'unknown'),
        })

    shots = []
    for idx, frame_path in enumerate(keyframe_paths[:6], start=1):
        shots.append({
            'shot_id': idx,
            'beat_id': min(idx, len(beats)),
            'time_range': beats[min(idx - 1, len(beats) - 1)]['time_range'] if beats else 'unknown',
            'shot_size': 'unknown',
            'camera_angle': 'unknown',
            'camera_movement': 'unknown',
            'subject': '需结合关键帧人工确认',
            'scene_task': '关键帧证据占位，等待视觉复核',
            'transition_in': 'unknown',
            'transition_out': 'unknown',
            'confidence': 'low',
        })

    if copy_profile['signals']:
        rhetorical_moves = copy_profile['signals']
    else:
        rhetorical_moves = []

    evidence_notes = [
        f"local_video_verified={video_path.exists()}",
        f"scene_change_count={len(scene_info.get('scene_times') or [])}",
    ]
    if contact_sheet:
        evidence_notes.append('contact_sheet_generated=true')
    if keyframe_paths:
        evidence_notes.append(f'keyframes_generated={len(keyframe_paths)}')

    risks = []
    unknowns = []
    if not keyframe_paths:
        risks.append('keyframes_missing')
        unknowns.append('no visual evidence frames extracted')
    risks.append('dialogue_not_transcribed')
    unknowns.append('spoken dialogue and字幕内容未转写')
    unknowns.append('景别、机位、运镜仍需人工或视觉模型复核')

    return {
        'analysis_version': '2.0.0',
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
            'source_depth': 'video_probe_plus_keyframes',
            'confidence': 'medium' if keyframe_paths else 'low',
            'prerequisites_passed': True,
            'video_download_verified': True,
            'notes': [
                'This analysis was built only after local video download was verified.',
                'Evidence includes ffprobe media profile, scene-cut estimation, extracted keyframes, and contact sheet assets.',
                'Dialogue, exact shot type, and semantic frame meaning still need manual or multimodal review for high confidence.',
            ] + evidence_notes,
        },
        'positioning': {
            'primary_goal': goal,
            'secondary_goals': ['engagement'] if goal != 'engagement' else [],
            'content_archetype': archetype,
            'sub_archetypes': copy_profile['hashtags'][:3],
            'target_audience': 'unknown',
        },
        'hook': {
            'hook_type': hook['hook_type'],
            'hook_text': desc[:80],
            'visual_hook': 'See contact sheet and keyframes for manual review',
            'emotion': hook['emotion'],
            'promise': hook['promise'],
            'time_range': beats[0]['time_range'] if beats else 'unknown',
        },
        'narrative': {
            'structure_formula': 'hook -> setup -> delivery -> payoff',
            'beats': beats,
        },
        'shot_plan': {
            'dominant_style': f"{media_profile.get('orientation', 'unknown')}_video_with_{pace_info.get('pace', 'unknown')}_editing",
            'shots': shots,
        },
        'dialogue': {
            'delivery_style': 'caption-led or voice-led, transcript missing',
            'structure': '由标题钩子驱动，台词内容需转写后确认',
            'rhetorical_moves': rhetorical_moves,
            'cta_type': 'none' if not re.search(r'评论|关注|私信|收藏|主页', desc) else 'unknown',
        },
        'editing_packaging': {
            'pace': pace_info.get('pace', 'unknown'),
            'subtitle_style': 'unknown',
            'transition_types': ['hard_cut_likely'] if (scene_info.get('scene_times') or []) else [],
            'packaging_elements': ['hashtags_in_caption'] if copy_profile['hashtags'] else [],
            'audio_strategy': 'has_music_or_audio_track' if media_profile.get('has_audio') else 'silent_or_unknown',
        },
        'persuasion': {
            'emotion_triggers': [hook['emotion']] if hook['emotion'] != 'unknown' else [],
            'credibility_signals': ['high_share_ratio'] if (ep.get('share_like_ratio') or 0) >= 0.08 else [],
            'conversion_devices': ['caption_contradiction_hook'] if 'inner_conflict' in copy_profile['signals'] else [],
        },
        'reusable_patterns': {
            'opening_formula': desc[:80],
            'structure_formula': 'short-form emotional hook -> quick context -> feeling delivery -> soft ending',
            'shot_formula': '先看 contact sheet 和关键帧，再决定是否可复用，不允许直接套壳',
            'dialogue_formula': '矛盾句式或短句直给，避免解释过满',
            'applicable_scenarios': ['情绪型短 vlog', '关系表达类内容', '轻叙事短视频'],
            'not_applicable_scenarios': ['严肃教程', '强信息密度知识类', '需要明确步骤演示的视频'],
        },
        'risks_and_limits': {
            'risk_flags': risks,
            'unknowns': unknowns,
        },
        'evidence': {
            'local_video_path': str(video_path),
            'media_profile': media_profile,
            'scene_info': scene_info,
            'editing_metrics': pace_info,
            'engagement_profile': ep,
            'copy_profile': copy_profile,
            'contact_sheet_path': str(contact_sheet) if contact_sheet else None,
            'keyframe_paths': [str(p) for p in keyframe_paths],
        },
    }


def write_markdown(md_path: Path, structured: Dict[str, Any]) -> None:
    video = structured['video']
    evidence = structured.get('evidence', {})
    media = evidence.get('media_profile', {})
    edit = evidence.get('editing_metrics', {})
    copy_profile = evidence.get('copy_profile', {})
    ep = evidence.get('engagement_profile', {})

    lines = [
        f"# Douyin Deep Video Analysis - {video.get('video_id')}",
        '',
        '## 结论先说',
        '- 这份分析只在本地视频已下载成功后生成。',
        '- 这不是只看描述文本的空分析，而是结合了本地视频探针、关键帧、联系图和节奏估算。',
        '- 但它仍然不是最终真相。没有字幕转写和视觉复核，景别/运镜/对白不允许写死。',
        '',
        '## 硬证据',
        f"- local_video_path: {evidence.get('local_video_path')}",
        f"- contact_sheet_path: {evidence.get('contact_sheet_path') or ''}",
        f"- keyframe_count: {len(evidence.get('keyframe_paths') or [])}",
        f"- duration_sec: {media.get('duration_sec')}",
        f"- resolution: {media.get('width')}x{media.get('height')}",
        f"- orientation: {media.get('orientation')}",
        f"- fps: {media.get('fps')}",
        f"- has_audio: {media.get('has_audio')}",
        f"- scene_change_count: {len((evidence.get('scene_info') or {}).get('scene_times') or [])}",
        f"- avg_shot_length_sec_est: {edit.get('avg_shot_length_sec')}",
        f"- editing_pace_est: {edit.get('pace')}",
        '',
        '## 表现信号',
        f"- digg_count: {ep.get('digg_count')}",
        f"- comment_count: {ep.get('comment_count')}",
        f"- collect_count: {ep.get('collect_count')}",
        f"- share_count: {ep.get('share_count')}",
        f"- comment_per_1k_likes: {ep.get('comment_per_1k_likes')}",
        f"- collect_per_1k_likes: {ep.get('collect_per_1k_likes')}",
        f"- share_per_1k_likes: {ep.get('share_per_1k_likes')}",
        '',
        '## 标题/文案信号',
        f"- desc: {video.get('desc') or ''}",
        f"- hashtags: {', '.join(copy_profile.get('hashtags') or [])}",
        f"- copy_signals: {', '.join(copy_profile.get('signals') or [])}",
        '',
        '## 当前可下的判断',
        f"- primary_goal: {structured['positioning'].get('primary_goal')}",
        f"- content_archetype: {structured['positioning'].get('content_archetype')}",
        f"- hook_type: {structured['hook'].get('hook_type')}",
        f"- emotion: {structured['hook'].get('emotion')}",
        f"- structure_formula: {structured['narrative'].get('structure_formula')}",
        '',
        '## 仍然不能乱写的部分',
    ]
    for item in structured.get('risks_and_limits', {}).get('unknowns', []):
        lines.append(f'- {item}')
    lines.extend([
        '',
        '## Structured analysis JSON',
        '```json',
        json.dumps(structured, ensure_ascii=False, indent=2),
        '```',
    ])
    md_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def update_mysql(dsn: Optional[str], normalized: Dict[str, Any], md_path: Path, video_path: Path) -> None:
    conn = with_mysql(dsn)
    if conn is None:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE videos
            SET local_video_path = COALESCE(local_video_path, %s),
                local_analysis_md_path = %s,
                download_status = %s,
                analysis_status = %s,
                downloaded_at = COALESCE(downloaded_at, NOW()),
                analyzed_at = NOW()
            WHERE aweme_id = %s
            """,
            (str(video_path), str(md_path), 'downloaded', 'completed', str(normalized.get('video_id') or '')),
        )
    conn.close()


def mark_blocked_mysql(dsn: Optional[str], video_id: str) -> None:
    conn = with_mysql(dsn)
    if conn is None:
        return
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE videos SET analysis_status = %s WHERE aweme_id = %s",
            ('blocked_missing_video', video_id),
        )
    conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description='Analyze a downloaded Douyin video deeply enough to produce evidence-backed markdown and structured JSON.')
    parser.add_argument('normalized_json')
    parser.add_argument('--mysql-dsn', default=os.getenv('MYSQL_DSN'))
    args = parser.parse_args()

    normalized_path = Path(args.normalized_json).expanduser().resolve()
    normalized = load_json(normalized_path)
    video_id = str(normalized.get('video_id') or normalized_path.stem)
    creator_slug = detect_creator_slug_from_path(normalized_path) or slugify(normalized.get('author_unique_id') or normalized.get('author_name') or 'unknown-creator')
    root = creator_root(creator_slug)
    video_path = find_video_file(normalized_path, normalized)
    if not video_path or not video_path.exists():
        mark_blocked_mysql(args.mysql_dsn, video_id)
        print(json.dumps({
            'ok': False,
            'reason': 'video_not_downloaded',
            'video_id': video_id,
            'expected_creator_root': str(root),
        }, ensure_ascii=False, indent=2))
        return 1

    artifacts_dir = root / 'analysis_assets' / video_id
    keyframes_dir = artifacts_dir / 'keyframes'
    probe = ffprobe_json(video_path)
    media_profile = extract_media_profile(probe)
    duration_sec = media_profile.get('duration_sec')
    scene_info = detect_scene_changes(video_path)
    timestamps = choose_sample_timestamps(duration_sec, count=9)
    keyframe_paths = extract_keyframes(video_path, keyframes_dir, timestamps)
    contact_sheet = build_contact_sheet(keyframes_dir, len(keyframe_paths), artifacts_dir / 'contact_sheet.jpg') if keyframe_paths else None

    structured = build_structured_analysis(normalized, video_path, media_profile, scene_info, keyframe_paths, contact_sheet)
    analysis_md_dir = root / 'analysis_md'
    analysis_md_dir.mkdir(parents=True, exist_ok=True)
    md_path = analysis_md_dir / f'{video_id}.md'
    write_markdown(md_path, structured)
    update_mysql(args.mysql_dsn, normalized, md_path, video_path)

    out = {
        'ok': True,
        'video_id': video_id,
        'creator_slug': creator_slug,
        'local_video_path': str(video_path),
        'analysis_md_path': str(md_path),
        'contact_sheet_path': str(contact_sheet) if contact_sheet else None,
        'keyframe_paths': [str(p) for p in keyframe_paths],
        'scene_change_count': len(scene_info.get('scene_times') or []),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
