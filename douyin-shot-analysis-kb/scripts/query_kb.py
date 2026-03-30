#!/usr/bin/env python3
"""Query a Haystack/Qdrant creator knowledge base."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[2]
if str(PACK_ROOT) not in sys.path:
    sys.path.insert(0, str(PACK_ROOT))

from common.haystack_rag import RagConfig, build_rag_context, call_llm_json, load_manifest, retrieve_from_manifest


def answer_with_llm(manifest: dict, question: str, top_k: int) -> dict:
    retrieved = retrieve_from_manifest(manifest, question, top_k=top_k, config=RagConfig())
    context = build_rag_context(retrieved)
    payload = call_llm_json(
        system_prompt=(
            '你是一个抖音拍摄知识库问答助手。必须只基于检索到的上下文回答。'
            '输出 JSON，字段包含 answer、evidence_video_ids、actionable_points、uncertainty。'
        ),
        user_prompt=f"问题: {question}\n\n检索上下文:\n{context}",
        config=RagConfig(),
    )
    payload['_retrieved'] = retrieved
    return payload


def answer_without_llm(manifest: dict, question: str, top_k: int) -> dict:
    retrieved = retrieve_from_manifest(manifest, question, top_k=top_k, config=RagConfig())
    return {
        'answer': '当前未检测到可用的 OpenAI 兼容 LLM 配置，返回最相关的知识块供后续脚本或人工使用。',
        'question': question,
        'evidence_video_ids': list(dict.fromkeys((item.get('meta') or {}).get('video_id') for item in retrieved if (item.get('meta') or {}).get('video_id'))),
        'actionable_points': [item.get('content', '')[:320] for item in retrieved[:6]],
        'uncertainty': ['未启用生成模型，answer 为检索结果摘要而非生成式推理。'],
        '_retrieved': retrieved,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('knowledge_base_json')
    parser.add_argument('question')
    parser.add_argument('--top-k', type=int, default=8)
    args = parser.parse_args()
    manifest = load_manifest(Path(args.knowledge_base_json).expanduser())
    cfg = RagConfig()
    result = answer_with_llm(manifest, args.question, args.top_k) if cfg.llm_available() else answer_without_llm(manifest, args.question, args.top_k)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
