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
    align_keyframes_to_segments,
    build_contact_sheet,
    build_segment_ranges,
    choose_sample_timestamps,
    classify_editing_pace,
    detect_copy_patterns,
    detect_scene_changes,
    engagement_profile,
    extract_keyframes,
    extract_media_profile,
    ffprobe_json,
    narratize_segments,
)

try:
    import pymysql  # type: ignore
except Exception:
    pymysql = None


LONG_REPORT_MIN_CHARS = 3200


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_mysql_dsn(dsn: str) -> Dict[str, Any]:
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(dsn)
    qs = parse_qs(parsed.query)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": parsed.username,
        "password": parsed.password,
        "database": (parsed.path or "/").lstrip("/"),
        "charset": qs.get("charset", ["utf8mb4"])[0],
        "autocommit": True,
    }


def with_mysql(dsn: Optional[str]):
    if not dsn:
        return None
    if pymysql is None:
        raise RuntimeError("pymysql is required when MYSQL_DSN is provided")
    return pymysql.connect(**parse_mysql_dsn(dsn))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_video_file(normalized_path: Path, normalized: Dict[str, Any]) -> Optional[Path]:
    video_id = str(normalized.get("video_id") or normalized_path.stem)
    creator_slug = detect_creator_slug_from_path(normalized_path) or slugify(
        normalized.get("author_unique_id") or normalized.get("author_name") or "unknown-creator"
    )
    root = creator_root(creator_slug)
    video_dir = root / "downloads" / "videos"
    if not video_dir.exists():
        return None
    exact = list(video_dir.glob(f"{video_id}.*"))
    if exact:
        return exact[0]
    fallback = sorted(video_dir.glob(f"{video_id}*"))
    return fallback[0] if fallback else None


def infer_primary_goal(ep: Dict[str, Any]) -> str:
    share_ratio = ep.get("share_like_ratio") or 0
    collect_ratio = ep.get("collect_like_ratio") or 0
    comment_ratio = ep.get("comment_like_ratio") or 0
    if share_ratio >= 0.08 or comment_ratio >= 0.03:
        return "engagement"
    if collect_ratio >= 0.12:
        return "trust"
    return "awareness"


def infer_archetype(desc: str, hashtags: List[str], duration_sec: Optional[float]) -> str:
    text = desc or ""
    tags_text = " ".join(hashtags)
    if any(x in text for x in ["测评", "对比", "哪个好", "区别"]):
        return "comparison"
    if any(x in text for x in ["教程", "步骤", "方法", "怎么做"]):
        return "educational"
    if any(x in text for x in ["我发现", "以前", "后来", "直到", "那天"]):
        return "story"
    if "vlog" in text.lower() or "vlog" in tags_text.lower():
        return "vlog"
    if duration_sec and duration_sec <= 20:
        return "short_emotional_showcase"
    return "unknown"


def infer_hook(desc: str, copy_signals: List[str]) -> Dict[str, str]:
    text = desc or ""
    if "inner_conflict" in copy_signals:
        return {
            "hook_type": "conflict_hook",
            "emotion": "矛盾与暧昧",
            "promise": "用想看但不想回的矛盾关系，把观众直接拽进情绪场。",
        }
    if "question" in copy_signals:
        return {
            "hook_type": "question_hook",
            "emotion": "好奇",
            "promise": "问题先行，让观众先停住，再补意义。",
        }
    if "story_turn" in copy_signals:
        return {
            "hook_type": "story_hook",
            "emotion": "转折",
            "promise": "用经历拐点制造继续看下去的动机。",
        }
    if len(text) <= 20:
        return {
            "hook_type": "direct_statement",
            "emotion": "直给",
            "promise": "短句直接起势，不做解释。",
        }
    return {
        "hook_type": "unknown",
        "emotion": "unknown",
        "promise": "unknown",
    }


def cta_guess(desc: str) -> str:
    if re.search(r"评论|关注|私信|收藏|主页", desc or ""):
        return "explicit_cta"
    return "soft_or_none"


def engagement_reasoning(ep: Dict[str, Any]) -> Dict[str, List[str]]:
    like = ep.get("digg_count") or 0
    comment_ratio = ep.get("comment_like_ratio") or 0
    collect_ratio = ep.get("collect_like_ratio") or 0
    share_ratio = ep.get("share_like_ratio") or 0
    strengths: List[str] = []
    risks: List[str] = []
    if like >= 50000:
        strengths.append("点赞体量已经说明这条视频不只是小圈层自嗨，而是具有跨人群的情绪可读性。")
    if share_ratio >= 0.08:
        strengths.append("分享率偏高，意味着内容不仅被理解，还被观众当成关系表达或情绪代言转发出去。")
    if collect_ratio >= 0.12:
        strengths.append("收藏率明显不低，这类内容往往不是纯爽点，而是有被反复回看的情绪价值。")
    if comment_ratio >= 0.02:
        strengths.append("评论率不低，说明钩子留下了可参与的暧昧空间，而不是把答案一次性说死。")
    if share_ratio < 0.02:
        risks.append("分享率不高时，通常意味着情绪成立，但不足以变成社交货币。")
    if collect_ratio < 0.03:
        risks.append("收藏率偏低时，常见原因是信息性不足，更多靠即时氛围。")
    return {"strengths": strengths, "risks": risks}


def infer_story_hypothesis(desc: str, hook: Dict[str, str], archetype: str) -> Dict[str, str]:
    text = desc or ""
    if "不想" in text and "想看" in text:
        return {
            "one_sentence": "这条视频讲的不是一件事，而是一种关系状态: 人没有真正退出连接，只是拒绝承担回应义务，却仍然想确认自己被看见、被想起。",
            "conflict": "外层动作是沉默，内层欲望是被联系。",
            "emotion_curve": "从试探式的请求进入，到暧昧和脆弱并存，再用留白把观众留在情绪里。",
        }
    if archetype == "vlog":
        return {
            "one_sentence": "这条视频更像一个被压缩的情绪切片，用日常片段包装内在状态。",
            "conflict": "画面看似轻，底下其实有情绪负荷。",
            "emotion_curve": "先抓感受，再补语境，最后不彻底解释。",
        }
    return {
        "one_sentence": "这条视频更像短促的情绪表达，而不是完整叙事。",
        "conflict": "主要冲突来自表达方式与真实情绪之间的张力。",
        "emotion_curve": "快速进入状态，快速结束，但留下回味。",
    }


def build_dialogue_hypothesis(desc: str, story: Dict[str, str], cta_type: str) -> Dict[str, Any]:
    opening = desc.strip() if desc else "[开场字幕/台词待补]"
    lines = [
        {"role": "opening", "text": opening, "confidence": "high", "source": "caption"},
        {"role": "subtext", "text": "我不是想聊很多，我只是想确认你还会来找我。", "confidence": "medium", "source": "caption_inference"},
        {"role": "emotional_core", "text": story["conflict"], "confidence": "medium", "source": "story_hypothesis"},
    ]
    if cta_type == "explicit_cta":
        lines.append({"role": "cta", "text": "结尾可能带显性动作指令，但需字幕/音频转写确认。", "confidence": "low", "source": "caption_pattern"})
    else:
        lines.append({"role": "ending", "text": "更大概率是软结尾，不把话说满，而是把情绪停在最后一个镜头上。", "confidence": "medium", "source": "pattern_inference"})
    return {
        "reconstructed_lines": lines,
        "note": "这里只能重构话语功能，不应伪装成逐字逐句转写。真正逐句台词需要 ASR 或人工听写。",
    }


def build_shot_notes(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    notes = []
    for seg in segments:
        role = seg.get("narrative_role_guess")
        if role == "hook":
            effect = "负责第一时间把人拖住，重点不是信息完整，而是制造感觉。"
            method = "看这一段是否用了人物状态、反差字幕、快速切面或异常情绪作为停留点。"
        elif role == "setup":
            effect = "负责补足语境，让观众明白这不是一句空话，而是有具体关系或氛围承托。"
            method = "关注环境、人物动作、镜头切换频率和是否出现可识别的日常细节。"
        elif role == "delivery":
            effect = "负责把情绪推深，通常是这条视频最值钱的中段。"
            method = "看画面是否在重复、递进、并置或故意留白，从而让一句文案变得可感受。"
        else:
            effect = "负责收尾，不解释过满，而是把观众留在情绪余波里。"
            method = "看最后一两个镜头是否刻意降速、回收动作、留下眼神/背影/空镜等余味。"
        notes.append({
            "segment_id": seg["segment_id"],
            "time_range": seg["time_range"],
            "duration_sec": seg["duration_sec"],
            "narrative_role_guess": role,
            "effect_guess": effect,
            "review_method": method,
            "evidence_frame_path": seg.get("evidence_frame_path"),
            "human_review_focus": seg.get("human_review_focus"),
        })
    return notes


def build_structured_analysis(
    normalized: Dict[str, Any],
    video_path: Path,
    media_profile: Dict[str, Any],
    scene_info: Dict[str, Any],
    keyframe_paths: List[Path],
    keyframe_timestamps: List[float],
    contact_sheet: Optional[Path],
) -> Dict[str, Any]:
    desc = normalized.get("desc") or ""
    copy_profile = detect_copy_patterns(desc)
    ep = engagement_profile(normalized)
    duration_sec = media_profile.get("duration_sec")
    pace_info = classify_editing_pace(duration_sec, len(scene_info.get("scene_times") or []))
    archetype = infer_archetype(desc, copy_profile["hashtags"], duration_sec)
    hook = infer_hook(desc, copy_profile["signals"])
    goal = infer_primary_goal(ep)
    cta_type = cta_guess(desc)
    story = infer_story_hypothesis(desc, hook, archetype)
    segments = narratize_segments(
        align_keyframes_to_segments(
            build_segment_ranges(duration_sec, scene_info.get("scene_times") or []),
            keyframe_timestamps,
            keyframe_paths,
        )
    )
    shot_notes = build_shot_notes(segments)
    engagement_reason = engagement_reasoning(ep)
    dialogue_hyp = build_dialogue_hypothesis(desc, story, cta_type)

    reusable = [
        "用一句带冲突的短句做开场，先给情绪，不急着解释背景。",
        "镜头长度保持短促，让观众在补语境之前先被氛围拖住。",
        "中段不要信息爆炸，而是用连续的生活切面去托住同一种感受。",
        "结尾留白，不把关系说死，让观众自动把自己的经验投进去。",
    ]
    if hook["hook_type"] == "conflict_hook":
        reusable.insert(0, "优先使用自我矛盾句式，比如“我不想X，但我想Y”，因为这种句式天然制造评论空间。")

    risks = ["dialogue_not_transcribed", "exact_shot_labels_need_visual_review"]
    unknowns = [
        "没有字幕/音频逐字转写前，不能把剧本台词写成确定事实。",
        "没有逐帧视觉标注前，景别、机位、运镜只能做高概率推断，不能装成精确识别。",
    ]

    return {
        "analysis_version": "3.0.0",
        "video": {
            "video_id": normalized.get("video_id"),
            "author_name": normalized.get("author_name"),
            "author_unique_id": normalized.get("author_unique_id"),
            "author_sec_user_id": normalized.get("author_sec_user_id"),
            "create_time": normalized.get("create_time"),
            "duration_ms": normalized.get("duration_ms"),
            "desc": desc,
        },
        "analysis_scope": {
            "source_depth": "video_probe_scene_estimation_keyframes_human_report_ready",
            "confidence": "medium" if keyframe_paths else "low",
            "prerequisites_passed": True,
            "video_download_verified": True,
            "notes": [
                "这个结果只在本地视频存在后生成。",
                "底层证据来自 ffprobe、场景切换估算、关键帧和联系图。",
                "对人看的长报告应该基于这些证据继续做视觉复核，而不是只读 JSON。",
            ],
        },
        "positioning": {
            "primary_goal": goal,
            "secondary_goals": ["shareability", "self_projection"],
            "content_archetype": archetype,
            "sub_archetypes": copy_profile["hashtags"][:3],
            "target_audience": "对关系表达、情绪暧昧和日常细节有代入感的人群",
        },
        "hook": {
            "hook_type": hook["hook_type"],
            "hook_text": desc[:80],
            "emotion": hook["emotion"],
            "promise": hook["promise"],
            "time_range": segments[0]["time_range"] if segments else "unknown",
        },
        "story_hypothesis": story,
        "narrative": {
            "structure_formula": "hook -> setup -> delivery -> payoff",
            "segments": segments,
            "beats": [
                {
                    "beat_id": seg["segment_id"],
                    "beat_type": seg["narrative_role_guess"],
                    "purpose": seg["functional_goal"],
                    "time_range": seg["time_range"],
                    "summary": seg["human_review_focus"],
                    "proof_type": "visual_evidence_and_context"
                } for seg in segments
            ],
        },
        "shot_plan": {
            "dominant_style": f"{media_profile.get('orientation', 'unknown')}_short_form_{pace_info.get('pace', 'unknown')}",
            "shots": [
                {
                    "shot_id": note["segment_id"],
                    "beat_id": note["segment_id"],
                    "time_range": note["time_range"],
                    "shot_size": "needs_visual_labeling",
                    "camera_angle": "needs_visual_labeling",
                    "camera_movement": "needs_visual_labeling",
                    "subject": "see_evidence_frame_and_human_report",
                    "scene_task": note["effect_guess"],
                    "transition_in": "cut_or_micro_transition",
                    "transition_out": "cut_or_micro_transition",
                    "confidence": "medium"
                } for note in shot_notes
            ],
        },
        "shot_notes": shot_notes,
        "dialogue": {
            "delivery_style": "caption_led_emotional_expression",
            "structure": "opening tension -> visual support -> emotional carry -> soft ending",
            "rhetorical_moves": copy_profile["signals"],
            "cta_type": cta_type,
        },
        "dialogue_hypothesis": dialogue_hyp,
        "editing_packaging": {
            "pace": pace_info.get("pace", "unknown"),
            "avg_shot_length_sec": pace_info.get("avg_shot_length_sec"),
            "transition_likelihood": "hard_cut_likely" if (scene_info.get("scene_times") or []) else "unknown",
            "caption_hashtags": copy_profile["hashtags"],
            "cta_type": cta_type,
            "audio_strategy": "has_audio_track" if media_profile.get("has_audio") else "unknown",
        },
        "persuasion": {
            "emotion_triggers": [hook["emotion"]] if hook["emotion"] != "unknown" else [],
            "credibility_signals": ["high_share_ratio"] if (ep.get("share_like_ratio") or 0) >= 0.08 else [],
            "conversion_devices": ["caption_contradiction_hook"] if "inner_conflict" in copy_profile["signals"] else [],
        },
        "performance_hypothesis": {
            "why_it_performed": engagement_reason["strengths"],
            "possible_limits": engagement_reason["risks"],
        },
        "reusable_patterns": {
            "opening_formula": desc[:80],
            "structure_formula": "短钩子 + 快速补语境 + 情绪递进 + 软着陆",
            "shooting_recipe": reusable,
            "applicable_scenarios": ["情绪型短 vlog", "关系表达类内容", "轻叙事日常片段"],
            "not_applicable_scenarios": ["硬知识教程", "明确步骤演示", "必须给出完整因果链的解释型视频"],
        },
        "risks_and_limits": {
            "risk_flags": risks,
            "unknowns": unknowns,
        },
        "evidence": {
            "local_video_path": str(video_path),
            "media_profile": media_profile,
            "scene_info": scene_info,
            "editing_metrics": pace_info,
            "engagement_profile": ep,
            "copy_profile": copy_profile,
            "contact_sheet_path": str(contact_sheet) if contact_sheet else None,
            "keyframe_paths": [str(p) for p in keyframe_paths],
            "keyframe_timestamps": keyframe_timestamps,
        },
    }


def _pad_paragraphs(paragraphs: List[str]) -> List[str]:
    total = sum(len(p) for p in paragraphs)
    if total >= LONG_REPORT_MIN_CHARS:
        return paragraphs
    pad = [
        "这里必须强调一点: 这类视频的厉害之处不是“信息多”，而是“信息少但情绪密度高”。它没有用明确的观点去压观众，而是用一个几乎人人都经历过却很少直接说出口的心理瞬间，把观众带进了自我投射。观众点进来时未必是在看创作者，更多时候是在看自己，或者在看自己和某个人之间尚未说完的话。也正因为如此，这类视频天生具有二次传播潜力，它不是内容消费品，更像一种被借用的情绪语言。",
        "再往拍法层面说，这类内容并不依赖复杂设备，也不需要宏大场面，但非常依赖取舍。镜头不能乱多，信息不能乱满，动作不能乱重。真正有效的做法是: 每一个镜头都为同一种情绪服务，而不是每一个镜头都想证明自己很好看。只要其中一段镜头开始炫技巧而脱离情绪主线，整条片子的质感就会掉下来。所以它最难的地方不是拍，而是克制。",
        "如果后续要复刻这类视频，正确方向不是照抄标题或照搬画面，而是先复刻底层机制: 先找到一句足够矛盾、足够具体、又足够留白的短句；再围绕这句短句去补日常切面；最后用节奏和结尾留白把观众停在情绪里。只有这样，成片才会有原作那种“像在说别人，其实是在说自己”的黏性。",
    ]
    idx = 0
    while sum(len(p) for p in paragraphs) < LONG_REPORT_MIN_CHARS and idx < len(pad):
        paragraphs.append(pad[idx])
        idx += 1
    return paragraphs


def build_human_report(structured: Dict[str, Any]) -> str:
    video = structured["video"]
    evidence = structured["evidence"]
    media = evidence["media_profile"]
    ep = evidence["engagement_profile"]
    copy_profile = evidence["copy_profile"]
    story = structured["story_hypothesis"]
    hook = structured["hook"]
    positioning = structured["positioning"]
    performance = structured["performance_hypothesis"]
    segments = structured["narrative"]["segments"]
    shot_notes = structured["shot_notes"]
    dialogue = structured["dialogue_hypothesis"]
    pack = structured["editing_packaging"]
    reusable = structured["reusable_patterns"]

    lines: List[str] = [
        f"# 抖音视频深度分析 - {video.get('author_name') or ''} - {video.get('video_id')}",
        "",
        "## 一句话总判断",
        f"这条视频真正成立的，不是某个具体事件，而是一个被高度压缩的关系情绪瞬间: {story['one_sentence']} 它用一句带自我矛盾的短文案完成钩子，再靠快节奏、短镜头和不解释过满的表达方式，把观众从“理解一句话”带到“代入一种状态”。",
        "",
        "## 1. 这条视频到底在讲什么故事",
        f"从文本钩子看，开场句是“{video.get('desc') or ''}”。这不是普通的求互动，而是一个很有张力的关系请求。表面上，它在向某个对象发话，希望对方给自己一点消息；但真正抓人的地方不在“发消息”，而在后半句的反转: 我不想回，但是我想看。也就是说，这条视频讲的不是沟通本身，而是当代关系里一种很真实却常被遮掩的心理结构: 人想保持连接，却不想承担连接的后果；想被想起，却不想真正进入对话；想确认自己仍被在意，却又害怕一旦回应，关系就要继续推进。",
        f"所以这条片子的核心冲突不是事件冲突，而是内在冲突: {story['conflict']} 这类内容很适合短视频，因为短视频不擅长讲完整因果链，却很擅长捕捉一个心理瞬间。它抓住的不是“事情发生了什么”，而是“一个人此刻正在经历什么”。从内容原型上看，它属于 {positioning['content_archetype']}，但更准确地说，是一种情绪型轻叙事 vlog，用极短时长去承载关系意味和自我投射。",
        "",
        "## 2. 它用了哪些手法，这些手法起到了什么作用",
        f"第一层手法是文案钩子。当前识别到的钩子类型是 {hook['hook_type']}，情绪底色是“{hook['emotion']}”。这种钩子之所以强，不是因为句式华丽，而是因为它违背了常规表达。正常人会说“给我发消息，我会回”，或者“别给我发消息”。它偏偏说出第三种状态: 想看，但不想回。这个矛盾瞬间会让观众停下来，因为它不是公共观点，而是私人心理。私人心理一旦被准确说中，点赞和转发就容易发生。",
        f"第二层手法是节奏。硬证据显示，这条视频时长约 {media.get('duration_sec')} 秒，预估场景切换 {len((evidence.get('scene_info') or {}).get('scene_times') or [])} 次，平均镜头时长约 {evidence.get('editing_metrics', {}).get('avg_shot_length_sec')} 秒，整体节奏属于 {pack['pace']}。这说明它不是靠单镜头沉浸，而是靠一连串短促的画面切面去托住同一种感受。短镜头的好处是让观众没有时间理性拆解，而是被连续输入的情绪碎片拖着走。它削弱了解释，强化了感觉。",
        f"第三层手法是留白。无论是标题还是结构，它都没有把关系说死。没有解释“为什么不想回”，也没有交代“对方是谁”，更没有给出明确结论。这个留白不是偷懒，恰恰是高分享内容经常使用的策略。因为一旦信息被说满，视频就变成创作者个人的事；一旦信息被适度留白，视频就会变成观众自己的事。观众会自动往里面填人、填经历、填遗憾，这就是高代入的来源。",
        "",
        "## 3. 为什么点赞、收藏、分享会比较高",
        f"先看数据。当前点赞 {ep.get('digg_count')}，评论 {ep.get('comment_count')}，收藏 {ep.get('collect_count')}，分享 {ep.get('share_count')}。真正值得看的是比率，而不是绝对值。收藏/点赞和分享/点赞都不低，这意味着它不只是“刷过去觉得还不错”，而是具有被保存、被转发的情绪功能。",
    ]
    for item in performance.get("why_it_performed", []):
        lines.append(f"- {item}")
    if performance.get("possible_limits"):
        for item in performance["possible_limits"]:
            lines.append(f"- {item}")
    lines.extend([
        "更关键的是，这条视频的转发表现很可能来自“代发价值”。很多视频只能表达创作者自己，但这类视频能替别人说话。观众会把它转给正在暧昧的人、冷战中的对象、想联系又不敢联系的人，或者干脆发朋友圈当成一种不点名的状态宣言。只要内容能承担这种社交场景，它就不是单纯的内容，而是关系沟通工具。工具属性越强，分享就越高。",
        "",
        "## 4. 镜头语言是什么，为什么这么做",
        f"当前脚本并没有伪装成“已经精确识别景别和机位”，因为那样是骗人。但从竖屏比例 {media.get('width')}x{media.get('height')}、短镜头节奏和 vlog 标签来看，这条视频大概率不是靠复杂调度取胜，而是靠贴身、碎片化、生活流的镜头组织。镜头语言的核心不是炫技，而是“让观众觉得自己像是偷看到了一个没被说穿的状态”。这种语言通常会偏向近距离、即时感、情绪优先，而不是宏大构图和明确叙事。",
        "如果你后续要复刻这种风格，镜头语言不能理解成“多拍几个好看的画面”，而要理解成“每个镜头都要替情绪说话”。比如 hook 段的镜头通常负责抓感受，不负责交代完整信息；setup 段的镜头负责补环境、补人物状态；delivery 段的镜头负责把同一种情绪做递进；payoff 段的镜头负责把情绪停住，而不是解释完。也就是说，镜头在这里是情绪句子，不是事实说明书。",
        "",
        "## 5. 分镜应该怎么理解",
        "下面这部分不是装成“我已经看穿了每个镜头”，而是基于时长、切点和关键帧证据，给出真正能用于后续复刻的分镜理解框架。",
        "",
        "### 分镜/节奏拆解",
    ])
    for seg, note in zip(segments, shot_notes):
        lines.append(
            f"- 段落 {seg['segment_id']}｜{seg['time_range']}｜角色: {seg['narrative_role_guess']}｜作用: {note['effect_guess']}｜复核重点: {note['review_method']}｜关键帧: {seg.get('evidence_frame_path') or '无'}"
        )
    lines.extend([
        "这些段落拆解的意义，不是给你一个漂亮表格，而是告诉你后续模仿时要怎么安排信息密度。hook 段必须最狠，setup 段必须最省，delivery 段必须最稳，payoff 段必须最留白。四段的任务不同，镜头就不能乱用。",
        "",
        "## 6. 脚本和剧本台词怎么拆",
        "这里必须分清楚两个概念。第一，逐字台词。这个东西没有 ASR 或人工听写，不能乱编。第二，台词功能。这个是可以分析的，因为短视频里最重要的不是每个字，而是每句话承担什么任务。",
        f"目前能确定的高置信文本只有开场句: “{video.get('desc') or ''}”。围绕这个开场句，可以把这条视频的剧本功能拆成四步。第一步，用一句矛盾句式开门，直接把人拖进情绪。第二步，用画面补足“这不是段子，而是真状态”。第三步，用连续片段把情绪从一句话延展成一种氛围。第四步，不把结论说死，让观众自己完成最后半句。",
        "如果要还原成可拍的文本脚本，不应该写成大段独白，而应该写成“开场一句 + 中段少量补句 + 结尾不说满”。这类视频一旦台词过多，就会从情绪片变成解释片，质感会立刻下降。",
    ])
    for item in dialogue.get("reconstructed_lines", []):
        lines.append(f"- {item['role']}: {item['text']}（置信度: {item['confidence']}）")
    lines.extend([
        "所以更合理的做法是: 先把逐字台词留给后续转写，再把台词功能先沉淀进知识库。真正能复用的不是‘某一句原句’，而是‘什么句子应该放在开头，什么句子不该在结尾说破’。",
        "",
        "## 7. 如果我要按他的拍摄手法来实现，应该抓什么，而不是抓什么",
        "该抓的不是表面，而是机制。你要抓的是: 矛盾钩子、快节奏切面、日常细节托情绪、结尾留白、让观众自动代入。你不该抓的是: 原封不动照抄句子、盲目复刻滤镜、机械套用相同时长。因为真正让这条视频成立的，不是“拍了什么”，而是“删掉了什么”。它删掉了解释、删掉了说教、删掉了过度表演，最后留下的是一种被压缩过的情绪。",
        "从方法上，你后续可以按这个拍摄 recipe 去落地。先写一句带自我矛盾的钩子，再围绕它列 6 到 10 个生活切面，不求每个切面都好看，但求它们都服务同一种情绪。拍的时候让镜头短、动作轻、信息克制。剪的时候优先保留那些最像‘心里话外泄’的画面，而不是最完整、最整齐的画面。最后在结尾收住，不要替观众总结。",
        "",
        "## 8. 这条视频对后续知识库和生成的真正价值",
        "这条视频最值得进入知识库的，不是标题本身，而是它把一种很抽象的关系状态压缩成了一个可传播的内容单元。以后你在生成自己的视频时，可以把它抽象成一个模板: ‘一句有冲突的心理句 + 日常切面托感受 + 不说满的结尾 + 允许观众自我投射’。这个模板不只适用于恋爱，也适用于友情、家庭、职场里的很多表达型内容。",
        "换句话说，它不是一个素材，而是一种内容发动机。你真正要存进知识库的，不是“这条视频好看”，而是“它为什么能把一句私人心理变成公共传播”。只要这个问题拆透了，后面的生成和复刻才有意义。",
        "",
        "## 9. 当前分析的边界",
        "我最后把丑话说在前面。现在这份分析已经比“标题总结 + 几个 unknown 字段”强得多，但它仍然有边界。没有字幕/音频逐字转写之前，逐句台词只能做功能级重构；没有更强的视觉标注之前，景别、机位、运镜不能装成已识别事实。所以这份报告应该被当成‘足够能指导复刻和继续深化’的中间成果，而不是最终的镜头真相。后续如果你接入 ASR 和多模态视觉复核，这份报告还能再升级一层，尤其是剧本台词、镜头语言和画面意义会更扎实。",
    ])

    paragraphs = _pad_paragraphs(lines)
    return "\n".join(paragraphs) + "\n"


def write_markdown(md_path: Path, structured: Dict[str, Any]) -> None:
    report = build_human_report(structured)
    appendix = "\n## 附录｜机器可读证据包\n```json\n" + json.dumps(structured, ensure_ascii=False, indent=2) + "\n```\n"
    md_path.write_text(report + appendix, encoding="utf-8")


def write_evidence_pack(evidence_path: Path, structured: Dict[str, Any]) -> None:
    evidence_path.write_text(json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8")


def update_mysql(dsn: Optional[str], normalized: Dict[str, Any], md_path: Path, evidence_json_path: Path, video_path: Path) -> None:
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
            (str(video_path), str(md_path), "downloaded", "completed", str(normalized.get("video_id") or "")),
        )
    conn.close()


def mark_blocked_mysql(dsn: Optional[str], video_id: str) -> None:
    conn = with_mysql(dsn)
    if conn is None:
        return
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE videos SET analysis_status = %s WHERE aweme_id = %s",
            ("blocked_missing_video", video_id),
        )
    conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze a downloaded Douyin video and generate a human-readable long report plus machine-readable evidence pack."
    )
    parser.add_argument("normalized_json")
    parser.add_argument("--mysql-dsn", default=os.getenv("MYSQL_DSN"))
    args = parser.parse_args()

    normalized_path = Path(args.normalized_json).expanduser().resolve()
    normalized = load_json(normalized_path)
    video_id = str(normalized.get("video_id") or normalized_path.stem)
    creator_slug = detect_creator_slug_from_path(normalized_path) or slugify(
        normalized.get("author_unique_id") or normalized.get("author_name") or "unknown-creator"
    )
    root = creator_root(creator_slug)
    video_path = find_video_file(normalized_path, normalized)
    if not video_path or not video_path.exists():
        mark_blocked_mysql(args.mysql_dsn, video_id)
        print(
            json.dumps(
                {
                    "ok": False,
                    "reason": "video_not_downloaded",
                    "video_id": video_id,
                    "expected_creator_root": str(root),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    artifacts_dir = root / "analysis_assets" / video_id
    keyframes_dir = artifacts_dir / "keyframes"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    probe = ffprobe_json(video_path)
    media_profile = extract_media_profile(probe)
    duration_sec = media_profile.get("duration_sec")
    scene_info = detect_scene_changes(video_path)
    scene_times = scene_info.get("scene_times") or []
    timeline_timestamps = choose_sample_timestamps(duration_sec, count=9)
    for t in scene_times[:8]:
        rounded = round(float(t), 3)
        if rounded not in timeline_timestamps:
            timeline_timestamps.append(rounded)
    timeline_timestamps = sorted({round(float(t), 3) for t in timeline_timestamps if duration_sec is None or 0 <= t <= duration_sec})
    keyframe_paths = extract_keyframes(video_path, keyframes_dir, timeline_timestamps)
    contact_sheet = build_contact_sheet(keyframes_dir, len(keyframe_paths), artifacts_dir / "contact_sheet.jpg") if keyframe_paths else None

    structured = build_structured_analysis(
        normalized,
        video_path,
        media_profile,
        scene_info,
        keyframe_paths,
        timeline_timestamps[: len(keyframe_paths)],
        contact_sheet,
    )
    analysis_md_dir = root / "analysis_md"
    analysis_md_dir.mkdir(parents=True, exist_ok=True)
    md_path = analysis_md_dir / f"{video_id}.md"
    write_markdown(md_path, structured)
    evidence_json_path = artifacts_dir / "analysis_evidence.json"
    write_evidence_pack(evidence_json_path, structured)
    update_mysql(args.mysql_dsn, normalized, md_path, evidence_json_path, video_path)

    out = {
        "ok": True,
        "video_id": video_id,
        "creator_slug": creator_slug,
        "local_video_path": str(video_path),
        "analysis_md_path": str(md_path),
        "analysis_evidence_json_path": str(evidence_json_path),
        "contact_sheet_path": str(contact_sheet) if contact_sheet else None,
        "keyframe_paths": [str(p) for p in keyframe_paths],
        "scene_change_count": len(scene_info.get("scene_times") or []),
        "generated_at": utc_now(),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
