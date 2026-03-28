---
name: douyin-video-analysis
description: Analyze a downloaded Douyin video only after local video download succeeds. Extract media evidence, scene-change estimates, keyframes, contact sheet, and write a structured per-video analysis markdown for downstream KB building. Use when the user wants real per-video analysis instead of metadata-only scaffolds.
compatibility: Works best when a single-video fetch has already produced normalized JSON and downloaded local video files under ~/.openclaw/workspace/data/creators/<creator-slug>/downloads/videos/.
metadata:
  author: OpenAI
  version: 1.0.0
  category: media-analysis
  upstream: douyin-single-video-fetcher
---

# Douyin Video Analysis

This skill exists to stop fake analysis.

## Hard rule

Do not generate a per-video analysis markdown unless the local video file exists and can be probed.

If the video file is missing:
- stop
- mark the status as blocked or pending
- tell the user the video has not been downloaded yet
- do not write a pretend analysis from caption text alone

## What this skill should do

1. verify local video exists
2. run ffprobe for media facts
3. estimate scene changes and editing pace
4. extract keyframes and build a contact sheet
5. write one evidence-backed markdown analysis file
6. embed structured JSON for downstream KB building
7. update MySQL analysis status to completed

## What this skill must not do

- must not treat caption text as full creative analysis
- must not claim exact shot size or camera motion certainty without visual review
- must not write “待下载” and still pretend the video was analyzed
- must not pollute the KB with low-confidence scaffold junk

## Inputs

Preferred input:
- `~/.openclaw/workspace/data/creators/<creator-slug>/normalized/douyin_single_video/<video_id>.json`

## Outputs

- `~/.openclaw/workspace/data/creators/<creator-slug>/analysis_md/<video_id>.md`
- `~/.openclaw/workspace/data/creators/<creator-slug>/analysis_assets/<video_id>/contact_sheet.jpg`
- `~/.openclaw/workspace/data/creators/<creator-slug>/analysis_assets/<video_id>/keyframes/frame_*.jpg`

## Suggested script

- `scripts/analyze_local_video.py`

## Review standard

A usable analysis should separate:
- hard evidence
- plausible hypotheses
- still unknown

If it cannot separate those three, it is not analysis, only filler.
