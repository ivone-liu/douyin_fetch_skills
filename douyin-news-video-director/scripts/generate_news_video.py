#!/usr/bin/env python3
"""Generate a news-driven short-video package from KBs and optionally submit it to Volcengine.

Usage:
python scripts/generate_news_video.py request.json
python scripts/generate_news_video.py request.json --kb path/to/knowledge-base.json --kb path/to/other.json --no-submit
"""
from __future__ import annotations

import argparse
import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

PACK_ROOT = Path(__file__).resolve().parents[2]
import sys
if str(PACK_ROOT) not in sys.path:
    sys.path.insert(0, str(PACK_ROOT))

from common.storage import (
    default_generated_script_dir,
    default_generated_video_dir,
    get_workspace_data_root,
    slugify,
)
from common.volcengine_video import VolcengineVideoClient, VolcengineVideoError


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def discover_kb_paths() -> List[Path]:
    root = get_workspace_data_root() / 'creators'
    return sorted(root.glob('*/kb/knowledge-base.json'))


def load_kbs(paths: List[Path]) -> List[Dict[str, Any]]:
    rows = []
    for path in paths:
        try:
            rows.append(load_json(path))
        except Exception:
            continue
    return rows


def aggregate_patterns(kbs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for kb in kbs:
        creator = kb.get('creator', {}) or {}
        creator_key = creator.get('unique_id') or creator.get('creator_key') or creator.get('display_name') or 'unknown'
        for pattern in kb.get('patterns', []) or []:
            category = str(pattern.get('category') or 'unknown')
            summary = str(pattern.get('summary') or '').strip()
            if not summary:
                continue
            key = (category, summary)
            bucket = buckets.setdefault(key, {
                'category': category,
                'summary': summary,
                'evidence_count': 0,
                'evidence_video_ids': set(),
                'creator_keys': set(),
                'pattern_ids': [],
            })
            bucket['evidence_count'] += int(pattern.get('evidence_count') or len(pattern.get('evidence_video_ids') or []) or 0)
            bucket['evidence_video_ids'].update(pattern.get('evidence_video_ids') or [])
            bucket['creator_keys'].add(creator_key)
            if pattern.get('pattern_id'):
                bucket['pattern_ids'].append(pattern['pattern_id'])
    rows = []
    for idx, bucket in enumerate(sorted(buckets.values(), key=lambda item: (item['evidence_count'], len(item['creator_keys'])), reverse=True), start=1):
        rows.append({
            'pattern_id': f"agg_{bucket['category']}_{idx:03d}",
            'category': bucket['category'],
            'summary': bucket['summary'],
            'evidence_count': bucket['evidence_count'],
            'evidence_video_ids': sorted(bucket['evidence_video_ids']),
            'creator_count': len(bucket['creator_keys']),
            'creator_keys': sorted(bucket['creator_keys']),
            'source_pattern_ids': bucket['pattern_ids'][:20],
        })
    return rows


def top_patterns(patterns: List[Dict[str, Any]], categories: List[str], limit: int = 5) -> List[Dict[str, Any]]:
    rows = [p for p in patterns if p.get('category') in set(categories)]
    return rows[:limit]


def first_summary(patterns: List[Dict[str, Any]], fallback: str) -> str:
    return patterns[0].get('summary') if patterns else fallback


def build_news_angle(request: Dict[str, Any], patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
    title = request.get('news_title') or request.get('title') or '未命名新闻'
    summary = request.get('news_summary') or request.get('summary') or ''
    audience = request.get('audience') or '泛用户'
    goal = request.get('goal') or '提高完播和互动'
    hook_patterns = top_patterns(patterns, ['hook_type', 'opening_formula'])
    structure_patterns = top_patterns(patterns, ['structure_formula', 'beat_type', 'content_archetype'])
    persuasion_patterns = top_patterns(patterns, ['emotion_trigger', 'conversion_device', 'credibility_signal'])
    shot_patterns = top_patterns(patterns, ['shot_formula', 'shot_size', 'camera_angle', 'camera_movement', 'scene_task'])
    packaging_patterns = top_patterns(patterns, ['editing_pace', 'transition_type', 'subtitle_style', 'packaging_element'])

    hook_summary = first_summary(hook_patterns, '反常识直给')
    structure_summary = first_summary(structure_patterns, 'hook -> event -> why it matters -> takeaway -> cta')
    persuasion_summary = first_summary(persuasion_patterns, '冲突与现实代价')
    shot_summary = first_summary(shot_patterns, '快速切镜 + 重点特写')
    packaging_summary = first_summary(packaging_patterns, '全程字幕 + 硬切节奏')

    angle = request.get('angle') or f"别把这条新闻当热闹看，它真正改变的是{audience}接下来的判断方式"
    return {
        'title': title,
        'summary': summary,
        'audience': audience,
        'goal': goal,
        'angle': angle,
        'hook_strategy': hook_summary,
        'structure_strategy': structure_summary,
        'persuasion_strategy': persuasion_summary,
        'shot_strategy': shot_summary,
        'packaging_strategy': packaging_summary,
    }


def build_script_package(request: Dict[str, Any], patterns: List[Dict[str, Any]], kb_paths: List[Path]) -> Dict[str, Any]:
    news = build_news_angle(request, patterns)
    title = news['title']
    summary = news['summary']
    audience = news['audience']
    takeaway = request.get('takeaway') or '这不是八卦，它会改变行业里接下来最现实的决策。'
    cta = request.get('cta') or '关注我，下一条继续拆这件事会怎么往下走。'
    voice_tone = request.get('voice_tone') or '冷静、直接、有判断'
    aspect_ratio = request.get('aspect_ratio') or '9:16'
    duration_seconds = int(request.get('duration_seconds') or request.get('max_duration_seconds') or 12)

    beats = [
        {
            'beat_id': 1,
            'purpose': 'hook',
            'script': request.get('hook_line') or f"{title}，大多数人只看到了表面热闹，但真正该警惕的是后面的连锁反应。",
            'visual_intent': '第一秒直接给出最强冲突画面或新闻核心对象',
            'on_screen_text': title,
        },
        {
            'beat_id': 2,
            'purpose': 'event',
            'script': f"先把新闻本身说清楚，用一句话讲明白发生了什么。{summary}".strip(),
            'visual_intent': '用新闻相关主体、场景、图标、屏幕界面或象征性动作让观众立刻知道事件本体',
            'on_screen_text': '发生了什么',
        },
        {
            'beat_id': 3,
            'purpose': 'why_it_matters',
            'script': request.get('impact_line') or f"真正重要的不是这条消息本身，而是它会怎样影响{audience}接下来的预期、成本和选择。",
            'visual_intent': '画面从事件转向后果，用更具压迫感或对比感的镜头强化影响',
            'on_screen_text': '为什么重要',
        },
        {
            'beat_id': 4,
            'purpose': 'insight',
            'script': request.get('insight_line') or f"我的判断是：{news['angle']}。这件事现在看像新闻，往后看其实是风向。",
            'visual_intent': '画面开始收束为观点表达，用更明确的主视觉和文字结论压住观众注意力',
            'on_screen_text': '我的判断',
        },
        {
            'beat_id': 5,
            'purpose': 'takeaway',
            'script': takeaway,
            'visual_intent': '结尾给出结果导向或行动提醒，让信息有落点',
            'on_screen_text': '结论',
        },
        {
            'beat_id': 6,
            'purpose': 'cta',
            'script': cta,
            'visual_intent': '最后半秒留出品牌感或账号动作指令',
            'on_screen_text': '关注获取后续拆解',
        },
    ]

    shot_plan = [
        {
            'shot_id': 1,
            'beat_id': 1,
            'duration_hint_sec': 2,
            'shot_prompt': f"高冲击力新闻开场，围绕“{title}”构造一秒抓人的主视觉，纵向短视频构图，{news['shot_strategy']}，{news['packaging_strategy']}，真实、现代、适合抖音新闻短视频",
        },
        {
            'shot_id': 2,
            'beat_id': 2,
            'duration_hint_sec': 2,
            'shot_prompt': f"快速交代事件本身，展示与“{title}”直接相关的主体、动作、环境或抽象符号，镜头节奏干脆，信息密度高",
        },
        {
            'shot_id': 3,
            'beat_id': 3,
            'duration_hint_sec': 2,
            'shot_prompt': f"从事件切到影响层，强调成本、风险、预期变化或行业震荡，画面更有压力感和对比感，突出‘为什么重要’",
        },
        {
            'shot_id': 4,
            'beat_id': 4,
            'duration_hint_sec': 2,
            'shot_prompt': f"把观点压实，画面服务于明确判断：{news['angle']}，减少花哨元素，突出结论和态度",
        },
        {
            'shot_id': 5,
            'beat_id': 5,
            'duration_hint_sec': 2,
            'shot_prompt': f"结尾镜头回到人、行业或未来趋势，给观众一个可带走的判断，节奏收束但不拖沓",
        },
    ]

    video_prompt = textwrap.dedent(f"""
    请生成一条适合抖音/短视频信息流的纵向新闻观点视频，时长尽量使用模型支持的最长时长，画幅 {aspect_ratio}。
    风格要求：{voice_tone}，节奏利落，不做拼接感强的碎片化镜头，而是一个完整可发布的短视频成片。
    内容主题：{title}
    核心新闻摘要：{summary}
    核心角度：{news['angle']}
    叙事结构：{news['structure_strategy']}
    说服重点：{news['persuasion_strategy']}
    镜头策略：{news['shot_strategy']}
    包装策略：{news['packaging_strategy']}
    分镜要求：
    1. 开头 1 到 2 秒必须直接抛出最强冲突或最反常识的新闻切口。
    2. 中段快速交代事件本身，再明确它为什么重要。
    3. 后段给出鲜明判断，而不是停留在新闻转述。
    4. 结尾留出一句明确结论和轻量 CTA。
    5. 画面、字幕感和镜头调度都要服务信息吸收，避免空镜堆砌。
    分镜草案：
    {json.dumps(shot_plan, ensure_ascii=False, indent=2)}
    旁白脚本草案：
    {json.dumps(beats, ensure_ascii=False, indent=2)}
    """).strip()

    negative_prompt = request.get('negative_prompt') or '低清晰度，肢体异常，字幕乱码，画面脏乱，过度卡通，过度夸张表情，过长静止镜头'

    return {
        'meta': {
            'created_at': datetime.now(timezone.utc).isoformat(),
            'request_title': title,
            'kb_paths': [str(p) for p in kb_paths],
            'kb_count': len(kb_paths),
            'pattern_count': len(patterns),
        },
        'news': news,
        'beats': beats,
        'shot_plan': shot_plan,
        'video_generation': {
            'provider': 'volcengine',
            'aspect_ratio': aspect_ratio,
            'duration_seconds': duration_seconds,
            'prompt': video_prompt,
            'negative_prompt': negative_prompt,
        },
        'notes': [
            'This package is grounded in repeated KB patterns, then adapted to the supplied news event.',
            'Use the generated prompt as the model input, but keep human review before publishing.',
            'Video generation quality still depends on the provider model and the exact API template configured in ~/.openclaw/.env.',
        ],
    }


def resolve_creator_slug(request: Dict[str, Any], kb_paths: List[Path], kbs: List[Dict[str, Any]]) -> str:
    if request.get('creator_slug'):
        return slugify(str(request['creator_slug']))
    if len(kb_paths) == 1 and kb_paths[0].parent.name == 'kb':
        return kb_paths[0].parent.parent.name
    if kbs:
        creator = kbs[0].get('creator', {}) or {}
        value = creator.get('unique_id') or creator.get('creator_key') or creator.get('display_name')
        if value:
            return slugify(str(value))
    return 'newsroom'


def save_package(package: Dict[str, Any], creator_slug: str, title: str) -> Dict[str, Path]:
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    slug = slugify(title)[:80]
    script_dir = default_generated_script_dir(creator_slug) / 'news_video'
    video_dir = default_generated_video_dir(creator_slug) / 'news_video' / f'{timestamp}_{slug}'
    script_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)
    package_path = script_dir / f'{timestamp}_{slug}.json'
    prompt_path = script_dir / f'{timestamp}_{slug}.prompt.txt'
    markdown_path = script_dir / f'{timestamp}_{slug}.md'
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding='utf-8')
    prompt_path.write_text(package['video_generation']['prompt'], encoding='utf-8')
    md_lines = [
        f"# News Video Package - {title}",
        '',
        '## Angle',
        package['news']['angle'],
        '',
        '## Beats',
    ]
    for beat in package['beats']:
        md_lines.append(f"### Beat {beat['beat_id']} - {beat['purpose']}")
        md_lines.append(beat['script'])
        md_lines.append('')
    md_lines.append('## Video Prompt')
    md_lines.append('```text')
    md_lines.append(package['video_generation']['prompt'])
    md_lines.append('```')
    markdown_path.write_text('\n'.join(md_lines) + '\n', encoding='utf-8')
    return {'package_json': package_path, 'prompt_txt': prompt_path, 'markdown': markdown_path, 'video_dir': video_dir}


def submit_to_volcengine(package: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    client = VolcengineVideoClient()
    generation = package['video_generation']
    request_context = {
        'prompt': generation['prompt'],
        'negative_prompt': generation.get('negative_prompt'),
        'aspect_ratio': generation.get('aspect_ratio'),
        'duration_seconds': generation.get('duration_seconds'),
        'model': client.config.model,
        'model_version': client.config.model_version,
        'package': package,
        'news': package.get('news'),
    }
    result = client.generate(request_context)
    result_urls = result.get('result_urls') or []
    if result_urls:
        result['downloaded_files'] = client.download_results(result_urls, output_dir)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('request_json')
    parser.add_argument('--kb', action='append', default=[])
    parser.add_argument('--no-submit', action='store_true')
    args = parser.parse_args()

    request = load_json(Path(args.request_json).expanduser())
    kb_paths = [Path(p).expanduser() for p in (args.kb or request.get('kb_paths') or [])]
    if not kb_paths:
        kb_paths = discover_kb_paths()
    kbs = load_kbs(kb_paths)
    if not kbs:
        raise SystemExit('No readable knowledge-base.json files were found. Build KBs first.')
    patterns = aggregate_patterns(kbs)
    package = build_script_package(request, patterns, kb_paths)
    creator_slug = resolve_creator_slug(request, kb_paths, kbs)
    paths = save_package(package, creator_slug, package['news']['title'])

    result: Dict[str, Any] = {
        'creator_slug': creator_slug,
        'saved_paths': {k: str(v) for k, v in paths.items()},
        'package': package,
    }

    submit = request.get('submit_video', True)
    if args.no_submit:
        submit = False

    if submit:
        try:
            generation_result = submit_to_volcengine(package, paths['video_dir'])
            (paths['video_dir'] / 'volcengine-result.json').write_text(json.dumps(generation_result, ensure_ascii=False, indent=2), encoding='utf-8')
            result['volcengine'] = generation_result
        except VolcengineVideoError as exc:
            result['volcengine_error'] = str(exc)
        except Exception as exc:
            result['volcengine_error'] = f'Unexpected generation error: {exc}'

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
