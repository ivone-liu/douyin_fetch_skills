#!/usr/bin/env python3
"""Generate a short-video script draft from a Haystack/Qdrant creator KB."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PACK_ROOT = Path(__file__).resolve().parents[2]
if str(PACK_ROOT) not in sys.path:
    sys.path.insert(0, str(PACK_ROOT))

from common.haystack_rag import (
    RagConfig,
    build_rag_context,
    call_llm_json,
    default_script_output,
    load_manifest,
    retrieve_from_manifest,
)


def build_retrieval_query(req: Dict[str, Any]) -> str:
    parts = [
        str(req.get('topic') or req.get('news_title') or req.get('product') or ''),
        str(req.get('audience') or ''),
        str(req.get('goal') or ''),
        str(req.get('tone') or req.get('voice_tone') or ''),
        str(req.get('angle') or ''),
        str(req.get('constraints') or ''),
    ]
    return ' | '.join([p for p in parts if p])


def fallback_script(req: Dict[str, Any], retrieved: List[Dict[str, Any]]) -> Dict[str, Any]:
    topic = req.get('topic') or req.get('news_title') or req.get('product') or '未命名主题'
    audience = req.get('audience') or '泛用户'
    goal = req.get('goal') or '提高完播和互动'
    snippets = [item.get('content', '')[:220] for item in retrieved[:4]]
    hook_line = f"别把{topic}只当成表面内容，真正该看的，是它背后正在变化的判断依据。"
    beats = [
        {'beat': 1, 'purpose': 'hook', 'script': hook_line, 'visual': '开头直接上最强信息或最强情绪镜头'},
        {'beat': 2, 'purpose': 'setup', 'script': f'用一句话把{audience}最关心的问题提出来。', 'visual': '快速补语境'},
        {'beat': 3, 'purpose': 'delivery', 'script': f'从知识库里的高频表达方式里抽一条逻辑，解释为什么这件事影响{goal}。', 'visual': '用连续切面托住情绪和判断'},
        {'beat': 4, 'purpose': 'payoff', 'script': '结尾不要说满，留一个更值得继续讨论的判断出口。', 'visual': '回收情绪，停在余味上'},
    ]
    return {
        'idea': {
            'topic_angle': topic,
            'audience': audience,
            'goal': goal,
        },
        'hook': {'line': hook_line},
        'beats': beats,
        'references': snippets,
        'risk_notes': ['当前未检测到可用 LLM，脚本为检索增强的模板草案。'],
    }


def llm_script(req: Dict[str, Any], retrieved: List[Dict[str, Any]]) -> Dict[str, Any]:
    context = build_rag_context(retrieved)
    schema_hint = {
        'idea': {'topic_angle': 'string', 'audience': 'string', 'goal': 'string'},
        'hook': {'line': 'string', 'why_it_works': 'string'},
        'beats': [{'beat': 1, 'purpose': 'hook/setup/delivery/payoff/cta', 'script': 'string', 'visual': 'string', 'on_screen_text': 'string'}],
        'shot_plan': [{'shot_id': 1, 'purpose': 'string', 'visual': 'string', 'movement': 'string'}],
        'cta': 'string',
        'fit_notes': ['string'],
        'risk_notes': ['string'],
        'retrieval_evidence_video_ids': ['string'],
    }
    return call_llm_json(
        system_prompt=(
            '你是抖音短视频编导。必须只基于检索到的知识库上下文生成脚本。'
            '不要直接抄原作者句子，要抽取可迁移的钩子、结构、镜头与节奏。'
            f'输出 JSON，结构参考: {json.dumps(schema_hint, ensure_ascii=False)}'
        ),
        user_prompt=(
            f"用户需求: {json.dumps(req, ensure_ascii=False)}\n\n"
            f"知识库检索上下文:\n{context}\n\n"
            '请生成一个可拍、可剪、可复用的短视频脚本。'
        ),
        config=RagConfig(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('knowledge_base_json')
    parser.add_argument('request_json')
    parser.add_argument('--output')
    parser.add_argument('--top-k', type=int, default=10)
    args = parser.parse_args()

    kb_path = Path(args.knowledge_base_json).expanduser()
    request_path = Path(args.request_json).expanduser()
    manifest = load_manifest(kb_path)
    req = json.loads(request_path.read_text(encoding='utf-8'))
    query = build_retrieval_query(req)
    retrieved = retrieve_from_manifest(manifest, query, top_k=args.top_k, config=RagConfig())
    cfg = RagConfig()
    result = llm_script(req, retrieved) if cfg.llm_available() else fallback_script(req, retrieved)
    result['_retrieved'] = retrieved[:6]

    if args.output:
        out_path = Path(args.output).expanduser()
    elif req.get('save_output', True):
        out_path = default_script_output(manifest, str(req.get('topic') or req.get('news_title') or req.get('product') or 'script'))
    else:
        out_path = None

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        result['_saved_to'] = str(out_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
