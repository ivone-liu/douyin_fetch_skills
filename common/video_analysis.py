from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def ffprobe_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"available": False, "reason": "file_missing"}
    if shutil.which("ffprobe") is None:
        return {"available": False, "reason": "ffprobe_not_installed"}
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return {"available": True, "data": json.loads(raw.decode("utf-8"))}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def _parse_fraction(value: str | None) -> Optional[float]:
    if not value:
        return None
    if "/" in value:
        a, b = value.split("/", 1)
        try:
            a_f = float(a)
            b_f = float(b)
            if b_f == 0:
                return None
            return a_f / b_f
        except Exception:
            return None
    try:
        return float(value)
    except Exception:
        return None


def extract_media_profile(probe: Dict[str, Any]) -> Dict[str, Any]:
    if not probe.get("available"):
        return {
            "probe_available": False,
            "probe_reason": probe.get("reason", "unknown"),
        }
    data = probe.get("data") or {}
    streams = data.get("streams") or []
    fmt = data.get("format") or {}
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
    width = int(video_stream.get("width") or 0) or None
    height = int(video_stream.get("height") or 0) or None
    duration = None
    for candidate in [fmt.get("duration"), video_stream.get("duration"), audio_stream.get("duration")]:
        try:
            if candidate not in (None, ""):
                duration = float(candidate)
                break
        except Exception:
            continue
    fps = _parse_fraction(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))
    bit_rate = None
    for candidate in [fmt.get("bit_rate"), video_stream.get("bit_rate"), audio_stream.get("bit_rate")]:
        try:
            if candidate not in (None, ""):
                bit_rate = int(float(candidate))
                break
        except Exception:
            continue
    rotation = None
    tags = video_stream.get("tags") or {}
    side_list = video_stream.get("side_data_list") or []
    if "rotate" in tags:
        try:
            rotation = int(tags["rotate"])
        except Exception:
            rotation = None
    if rotation is None:
        for item in side_list:
            if isinstance(item, dict) and "rotation" in item:
                try:
                    rotation = int(float(item["rotation"]))
                    break
                except Exception:
                    pass
    aspect_ratio = None
    orientation = "unknown"
    if width and height:
        g = math.gcd(width, height)
        aspect_ratio = f"{width // g}:{height // g}" if g else f"{width}:{height}"
        orientation = "vertical" if height > width else "horizontal" if width > height else "square"
    return {
        "probe_available": True,
        "duration_sec": round(duration, 3) if duration is not None else None,
        "width": width,
        "height": height,
        "aspect_ratio": aspect_ratio,
        "orientation": orientation,
        "fps": round(fps, 3) if fps is not None else None,
        "bit_rate": bit_rate,
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
        "has_audio": bool(audio_stream),
        "rotation": rotation,
        "video_stream": {
            "pix_fmt": video_stream.get("pix_fmt"),
            "profile": video_stream.get("profile"),
        },
        "audio_stream": {
            "sample_rate": audio_stream.get("sample_rate"),
            "channels": audio_stream.get("channels"),
            "channel_layout": audio_stream.get("channel_layout"),
        } if audio_stream else {},
    }


def detect_scene_changes(video_path: Path, threshold: float = 0.28) -> Dict[str, Any]:
    if shutil.which("ffmpeg") is None:
        return {"available": False, "reason": "ffmpeg_not_installed", "scene_times": []}
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        str(video_path),
        "-filter:v",
        f"select='gt(scene,{threshold})',showinfo",
        "-vsync",
        "vfr",
        "-an",
        "-f",
        "null",
        "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        log = (proc.stderr or "") + "\n" + (proc.stdout or "")
        values = []
        for match in re.finditer(r"pts_time:([0-9.]+)", log):
            try:
                values.append(round(float(match.group(1)), 3))
            except Exception:
                continue
        seen = []
        seen_set = set()
        for item in values:
            if item not in seen_set:
                seen.append(item)
                seen_set.add(item)
        return {"available": True, "threshold": threshold, "scene_times": seen}
    except Exception as exc:
        return {"available": False, "reason": str(exc), "scene_times": []}


def classify_editing_pace(duration_sec: Optional[float], scene_change_count: int) -> Dict[str, Any]:
    if not duration_sec or duration_sec <= 0:
        return {"pace": "unknown", "avg_shot_length_sec": None, "scene_density_per_sec": None}
    shot_count_est = max(1, scene_change_count + 1)
    avg_shot_length = duration_sec / shot_count_est
    scene_density = scene_change_count / duration_sec
    if avg_shot_length <= 0.9:
        pace = "very_fast"
    elif avg_shot_length <= 1.8:
        pace = "fast"
    elif avg_shot_length <= 3.5:
        pace = "medium"
    else:
        pace = "slow"
    return {
        "pace": pace,
        "avg_shot_length_sec": round(avg_shot_length, 3),
        "scene_density_per_sec": round(scene_density, 3),
    }


def choose_sample_timestamps(duration_sec: Optional[float], count: int = 9) -> List[float]:
    if not duration_sec or duration_sec <= 0:
        return [0.0]
    if count <= 1:
        return [round(min(0.5, max(duration_sec / 2.0, 0.0)), 3)]
    safe_start = min(0.3, duration_sec * 0.05)
    safe_end = max(duration_sec - 0.3, safe_start)
    if safe_end <= safe_start:
        return [round(duration_sec / 2.0, 3)]
    step = (safe_end - safe_start) / (count - 1)
    return [round(safe_start + i * step, 3) for i in range(count)]


def extract_keyframes(video_path: Path, out_dir: Path, timestamps: List[float]) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: List[Path] = []
    if shutil.which("ffmpeg") is None:
        return frames
    for idx, ts in enumerate(timestamps, start=1):
        frame_path = out_dir / f"frame_{idx:02d}.jpg"
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            str(ts),
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(frame_path),
        ]
        subprocess.run(cmd, check=False)
        if frame_path.exists():
            frames.append(frame_path)
    return frames


def build_contact_sheet(frame_dir: Path, count: int, output_path: Path) -> Optional[Path]:
    if shutil.which("ffmpeg") is None:
        return None
    if count <= 0:
        return None
    cols = min(3, max(1, math.ceil(math.sqrt(count))))
    rows = max(1, math.ceil(count / cols))
    input_pattern = frame_dir / "frame_%02d.jpg"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_pattern),
        "-frames:v",
        "1",
        "-vf",
        f"tile={cols}x{rows}",
        str(output_path),
    ]
    subprocess.run(cmd, check=False)
    return output_path if output_path.exists() else None


def extract_hashtags(desc: str) -> List[str]:
    seen = []
    for tag in re.findall(r"#([^#\s]+)", desc or ""):
        tag = tag.strip()
        if tag and tag not in seen:
            seen.append(tag)
    return seen


def detect_copy_patterns(desc: str) -> Dict[str, Any]:
    desc = desc or ""
    signals: List[str] = []
    if any(ch in desc for ch in ["？", "?"]):
        signals.append("question")
    if re.search(r"不想.{0,12}但是.{0,12}想", desc):
        signals.append("inner_conflict")
    if re.search(r"可以.*吗", desc):
        signals.append("permission_ask")
    if any(x in desc for x in ["清单", "合集", "推荐", "盘点"]):
        signals.append("list_promise")
    if any(x in desc for x in ["我发现", "后来", "直到", "以前"]):
        signals.append("story_turn")
    return {
        "length_chars": len(desc),
        "hashtags": extract_hashtags(desc),
        "signals": signals,
    }


def engagement_profile(normalized: Dict[str, Any]) -> Dict[str, Any]:
    digg = int(normalized.get("digg_count") or 0)
    comment = int(normalized.get("comment_count") or 0)
    collect = int(normalized.get("collect_count") or 0)
    share = int(normalized.get("share_count") or 0)
    play = int(normalized.get("play_count") or 0)

    def ratio(n: int, d: int) -> Optional[float]:
        if not d:
            return None
        return round(n / d, 4)

    def per_k(n: int, d: int) -> Optional[float]:
        if not d:
            return None
        return round((n / d) * 1000, 2)

    return {
        "digg_count": digg,
        "comment_count": comment,
        "collect_count": collect,
        "share_count": share,
        "play_count": play,
        "comment_like_ratio": ratio(comment, digg),
        "collect_like_ratio": ratio(collect, digg),
        "share_like_ratio": ratio(share, digg),
        "comment_per_1k_likes": per_k(comment, digg),
        "collect_per_1k_likes": per_k(collect, digg),
        "share_per_1k_likes": per_k(share, digg),
    }
