from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common.storage import default_generated_script_dir, get_workspace_data_root, slugify

DEFAULT_QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
DEFAULT_QDRANT_COLLECTION_PREFIX = os.getenv("HAYSTACK_QDRANT_COLLECTION_PREFIX", "douyin_creator")
DEFAULT_LOCAL_EMBEDDING_MODEL = os.getenv("HAYSTACK_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass
class RagConfig:
    qdrant_mode: str = field(default_factory=lambda: os.getenv("HAYSTACK_QDRANT_MODE", "auto"))
    qdrant_url: str = field(default_factory=lambda: os.getenv("QDRANT_URL", DEFAULT_QDRANT_URL))
    qdrant_path: Optional[str] = field(default_factory=lambda: os.getenv("HAYSTACK_QDRANT_PATH"))
    qdrant_api_key: Optional[str] = field(default_factory=lambda: os.getenv("QDRANT_API_KEY"))
    collection_prefix: str = field(default_factory=lambda: os.getenv("HAYSTACK_QDRANT_COLLECTION_PREFIX", DEFAULT_QDRANT_COLLECTION_PREFIX))
    embedding_backend: str = field(default_factory=lambda: os.getenv("HAYSTACK_EMBEDDER_BACKEND", "auto"))
    local_embedding_model: str = field(default_factory=lambda: os.getenv("HAYSTACK_EMBEDDING_MODEL", DEFAULT_LOCAL_EMBEDDING_MODEL))
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY") or os.getenv("OPENCLAW_API_KEY"))
    openai_api_base: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_BASE") or os.getenv("OPENCLAW_API_BASE") or os.getenv("OPENAI_BASE_URL"))
    openai_embedding_model: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_EMBEDDING_MODEL") or os.getenv("OPENCLAW_EMBEDDING_MODEL"))
    llm_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY") or os.getenv("OPENCLAW_API_KEY"))
    llm_api_base: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_BASE") or os.getenv("OPENCLAW_API_BASE") or os.getenv("OPENAI_BASE_URL"))
    llm_model: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_MODEL") or os.getenv("OPENCLAW_MODEL") or os.getenv("MODEL"))

    def resolved_embedding_backend(self) -> str:
        backend = (self.embedding_backend or "auto").strip().lower()
        if backend in {"openai", "sentence_transformers"}:
            return backend
        if self.openai_embedding_model and (self.openai_api_base or self.openai_api_key or os.getenv("OPENCLAW_ALLOW_EMPTY_API_KEY", "1") == "1"):
            return "openai"
        return "sentence_transformers"

    def embedding_model_name(self) -> str:
        if self.resolved_embedding_backend() == "openai":
            return self.openai_embedding_model or "text-embedding-3-small"
        return self.local_embedding_model

    def llm_available(self) -> bool:
        return bool(self.llm_model and (self.llm_api_base or self.llm_api_key or os.getenv("OPENCLAW_ALLOW_EMPTY_API_KEY", "1") == "1"))

    def resolved_qdrant_mode(self) -> str:
        mode = (self.qdrant_mode or "auto").strip().lower()
        if mode in {"server", "local", "memory"}:
            return mode
        if self.qdrant_path:
            return "local"
        if self.qdrant_url and str(self.qdrant_url).strip():
            return "server"
        return "local"

    def resolved_qdrant_location(self) -> str:
        mode = self.resolved_qdrant_mode()
        if mode == "memory":
            return ":memory:"
        if mode == "local":
            raw = self.qdrant_path or str(get_workspace_data_root() / "qdrant_local")
            path = Path(raw).expanduser().resolve()
            path.mkdir(parents=True, exist_ok=True)
            return str(path)
        return (self.qdrant_url or DEFAULT_QDRANT_URL).strip() or DEFAULT_QDRANT_URL

    def qdrant_manifest_meta(self) -> Dict[str, Any]:
        mode = self.resolved_qdrant_mode()
        location = self.resolved_qdrant_location()
        meta: Dict[str, Any] = {"mode": mode}
        if mode in {"local", "memory"}:
            meta["location"] = location
        else:
            meta["url"] = location
        return meta


def _import_haystack_bits() -> Dict[str, Any]:
    try:
        from haystack import Document
        from haystack.components.embedders import (
            OpenAIDocumentEmbedder,
            OpenAITextEmbedder,
            SentenceTransformersDocumentEmbedder,
            SentenceTransformersTextEmbedder,
        )
        from haystack.components.generators.chat import OpenAIChatGenerator
        from haystack.dataclasses import ChatMessage
        from haystack.utils import Secret
        from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
        from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
    except Exception as exc:
        raise RuntimeError(
            "Haystack/Qdrant 依赖缺失。请先执行 install.sh 或 pip install -r requirements.txt。"
        ) from exc
    return {
        "Document": Document,
        "OpenAIDocumentEmbedder": OpenAIDocumentEmbedder,
        "OpenAITextEmbedder": OpenAITextEmbedder,
        "SentenceTransformersDocumentEmbedder": SentenceTransformersDocumentEmbedder,
        "SentenceTransformersTextEmbedder": SentenceTransformersTextEmbedder,
        "OpenAIChatGenerator": OpenAIChatGenerator,
        "ChatMessage": ChatMessage,
        "Secret": Secret,
        "QdrantDocumentStore": QdrantDocumentStore,
        "QdrantEmbeddingRetriever": QdrantEmbeddingRetriever,
    }


def load_manifest(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collection_name_for_creator(creator_slug: str, prefix: Optional[str] = None) -> str:
    safe = slugify(creator_slug).replace("-", "_")
    base = prefix or DEFAULT_QDRANT_COLLECTION_PREFIX
    return f"{base}_{safe}_analysis"[:120]


def extract_structured_json(text: str) -> Dict[str, Any]:
    for match in JSON_BLOCK_RE.finditer(text):
        candidate = match.group(1)
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and (data.get("analysis_version") or data.get("video") or data.get("positioning")):
            return data
    return {}


def strip_json_appendix(text: str) -> str:
    marker = "## 附录｜机器可读证据包"
    if marker in text:
        return text.split(marker, 1)[0].strip()
    return text.strip()


def split_markdown_sections(text: str) -> List[Tuple[str, str]]:
    clean = strip_json_appendix(text)
    if not clean:
        return []
    lines = clean.splitlines()
    sections: List[Tuple[str, List[str]]] = []
    current_title = "总览"
    buffer: List[str] = []
    for line in lines:
        if line.startswith("## "):
            if buffer:
                sections.append((current_title, buffer[:]))
            current_title = line[3:].strip() or "未命名章节"
            buffer = []
        else:
            buffer.append(line)
    if buffer:
        sections.append((current_title, buffer[:]))
    out: List[Tuple[str, str]] = []
    for title, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if body:
            out.append((title, body))
    return out


def chunk_text(text: str, max_chars: int = 900, min_chars: int = 220) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if current and len(candidate) > max_chars:
            if len(current) >= min_chars:
                chunks.append(current.strip())
                current = para
            else:
                current = candidate
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())
    merged: List[str] = []
    for chunk in chunks:
        if merged and len(chunk) < min_chars:
            merged[-1] = f"{merged[-1]}\n\n{chunk}".strip()
        else:
            merged.append(chunk)
    return merged


def infer_creator_slug_from_md(md_path: Path, structured: Dict[str, Any]) -> str:
    if "creators" in md_path.parts:
        idx = md_path.parts.index("creators")
        if idx + 1 < len(md_path.parts):
            return md_path.parts[idx + 1]
    video = structured.get("video") or {}
    return slugify(video.get("author_unique_id") or video.get("author_name") or md_path.parent.name)


def build_structured_fact_text(structured: Dict[str, Any]) -> str:
    video = structured.get("video") or {}
    positioning = structured.get("positioning") or {}
    hook = structured.get("hook") or {}
    story = structured.get("story_hypothesis") or {}
    narrative = structured.get("narrative") or {}
    dialogue = structured.get("dialogue_hypothesis") or {}
    reusable = structured.get("reusable_patterns") or {}
    performance = structured.get("performance_hypothesis") or {}
    lines = [
        f"视频ID: {video.get('video_id')}",
        f"作者: {video.get('author_name')}",
        f"标题/描述: {video.get('desc') or ''}",
        f"主要目标: {positioning.get('primary_goal')}",
        f"内容原型: {positioning.get('content_archetype')}",
        f"钩子类型: {hook.get('hook_type')}",
        f"钩子承诺: {hook.get('promise')}",
        f"故事假设: {story.get('one_sentence')}",
        f"核心冲突: {story.get('conflict')}",
        f"结构公式: {narrative.get('structure_formula')}",
        f"对话假设: {dialogue.get('note')}",
        f"开场公式: {reusable.get('opening_formula')}",
        f"复用结构: {reusable.get('structure_formula')}",
    ]
    for item in performance.get("why_it_performed", [])[:4]:
        lines.append(f"高表现原因: {item}")
    for item in (reusable.get("shooting_recipe") or [])[:6]:
        lines.append(f"拍摄配方: {item}")
    return "\n".join(x for x in lines if x and str(x).strip())


def build_documents_from_markdown(md_path: Path) -> Tuple[List[Any], Dict[str, Any]]:
    bits = _import_haystack_bits()
    Document = bits["Document"]
    text = md_path.read_text(encoding="utf-8")
    structured = extract_structured_json(text)
    creator_slug = infer_creator_slug_from_md(md_path, structured)
    video = structured.get("video") or {}
    video_id = str(video.get("video_id") or md_path.stem)
    positioning = structured.get("positioning") or {}
    hook = structured.get("hook") or {}
    analysis_scope = structured.get("analysis_scope") or {}
    common_meta = {
        "creator_slug": creator_slug,
        "video_id": video_id,
        "source_path": str(md_path),
        "primary_goal": positioning.get("primary_goal") or "unknown",
        "content_archetype": positioning.get("content_archetype") or "unknown",
        "hook_type": hook.get("hook_type") or "unknown",
        "confidence": analysis_scope.get("confidence") or "unknown",
        "source_depth": analysis_scope.get("source_depth") or "unknown",
    }
    docs: List[Any] = []
    for section_title, section_body in split_markdown_sections(text):
        for idx, chunk in enumerate(chunk_text(section_body), start=1):
            docs.append(
                Document(
                    content=f"[{section_title}]\n{chunk}",
                    meta={**common_meta, "section_title": section_title, "chunk_kind": "report_section", "chunk_index": idx},
                )
            )
    if structured:
        docs.append(
            Document(
                content=build_structured_fact_text(structured),
                meta={**common_meta, "section_title": "结构化事实", "chunk_kind": "structured_facts", "chunk_index": 1},
            )
        )
    summary = {
        "video_id": video_id,
        "doc_count": len(docs),
        "primary_goal": common_meta["primary_goal"],
        "content_archetype": common_meta["content_archetype"],
        "hook_type": common_meta["hook_type"],
        "source_path": str(md_path),
    }
    return docs, summary


def build_documents_from_analysis_dir(analysis_dir: Path) -> Tuple[List[Any], List[Dict[str, Any]], str]:
    all_docs: List[Any] = []
    summaries: List[Dict[str, Any]] = []
    creator_slug = analysis_dir.parent.name if analysis_dir.parent.name else "unknown-creator"
    for md_path in sorted(analysis_dir.glob("*.md")):
        docs, summary = build_documents_from_markdown(md_path)
        all_docs.extend(docs)
        summaries.append(summary)
        creator_slug = summary.get("source_path", "").split("/creators/")[-1].split("/")[0] or creator_slug
    return all_docs, summaries, creator_slug


def get_document_store(collection_name: str, embedding_dim: int, recreate: bool = False, config: Optional[RagConfig] = None):
    cfg = config or RagConfig()
    bits = _import_haystack_bits()
    kwargs: Dict[str, Any] = {
        "index": collection_name,
        "embedding_dim": embedding_dim,
        "recreate_index": recreate,
        "wait_result_from_api": True,
        "return_embedding": False,
    }
    mode = cfg.resolved_qdrant_mode()
    location = cfg.resolved_qdrant_location()
    if mode in {"local", "memory"}:
        return bits["QdrantDocumentStore"](location, **kwargs)
    kwargs["url"] = location
    if cfg.qdrant_api_key:
        kwargs["api_key"] = bits["Secret"].from_token(cfg.qdrant_api_key)
    return bits["QdrantDocumentStore"](**kwargs)


def get_embedders(config: Optional[RagConfig] = None):
    cfg = config or RagConfig()
    bits = _import_haystack_bits()
    backend = cfg.resolved_embedding_backend()
    if backend == "openai":
        token = cfg.openai_api_key or os.getenv("OPENCLAW_DUMMY_API_KEY", "not-needed")
        secret = bits["Secret"].from_token(token)
        common: Dict[str, Any] = {"api_key": secret, "model": cfg.embedding_model_name()}
        if cfg.openai_api_base:
            common["api_base_url"] = cfg.openai_api_base
        doc_embedder = bits["OpenAIDocumentEmbedder"](**common)
        text_embedder = bits["OpenAITextEmbedder"](**common)
        return doc_embedder, text_embedder, backend, cfg.embedding_model_name()
    doc_embedder = bits["SentenceTransformersDocumentEmbedder"](model=cfg.embedding_model_name())
    text_embedder = bits["SentenceTransformersTextEmbedder"](model=cfg.embedding_model_name())
    if hasattr(doc_embedder, "warm_up"):
        doc_embedder.warm_up()
    if hasattr(text_embedder, "warm_up"):
        text_embedder.warm_up()
    return doc_embedder, text_embedder, backend, cfg.embedding_model_name()


def index_analysis_dir_to_qdrant(analysis_dir: Path, output_dir: Path, recreate: bool = True, config: Optional[RagConfig] = None) -> Dict[str, Any]:
    cfg = config or RagConfig()
    documents, video_summaries, creator_slug = build_documents_from_analysis_dir(analysis_dir)
    if not documents:
        raise RuntimeError(f"No markdown analysis files found under: {analysis_dir}")
    doc_embedder, _, backend, model_name = get_embedders(cfg)
    embedded_docs = doc_embedder.run(documents=documents)["documents"]
    first_embedding = getattr(embedded_docs[0], "embedding", None) or []
    if not first_embedding:
        raise RuntimeError("Document embeddings were not generated. Check embedding model configuration.")
    embedding_dim = len(first_embedding)
    collection_name = collection_name_for_creator(creator_slug, cfg.collection_prefix)
    document_store = get_document_store(collection_name, embedding_dim=embedding_dim, recreate=recreate, config=cfg)
    document_store.write_documents(embedded_docs)
    output_dir.mkdir(parents=True, exist_ok=True)
    qdrant_meta = cfg.qdrant_manifest_meta()
    manifest = {
        "kb_version": "haystack_qdrant_v2",
        "creator_slug": creator_slug,
        "analysis_dir": str(analysis_dir),
        "qdrant": {
            **qdrant_meta,
            "collection_name": collection_name,
            "embedding_backend": backend,
            "embedding_model": model_name,
            "embedding_dim": embedding_dim,
        },
        "dataset": {
            "video_count": len(video_summaries),
            "chunk_count": len(embedded_docs),
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        },
        "videos": video_summaries,
    }
    (output_dir / "knowledge-base.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    qdrant_lines = [f"- qdrant_mode: {qdrant_meta['mode']}"]
    if qdrant_meta["mode"] in {"local", "memory"}:
        qdrant_lines.append(f"- qdrant_location: {qdrant_meta['location']}")
    else:
        qdrant_lines.append(f"- qdrant_url: {qdrant_meta['url']}")
    overview_lines = [
        f"# {creator_slug} RAG Knowledge Base",
        "",
        "## Storage",
        *qdrant_lines,
        f"- collection_name: {collection_name}",
        f"- embedding_backend: {backend}",
        f"- embedding_model: {model_name}",
        f"- embedding_dim: {embedding_dim}",
        "",
        "## Dataset",
        f"- video_count: {len(video_summaries)}",
        f"- chunk_count: {len(embedded_docs)}",
        f"- analysis_dir: {analysis_dir}",
        "",
        "## Sample videos",
    ]
    for item in video_summaries[:20]:
        overview_lines.append(f"- {item['video_id']} | {item['content_archetype']} | {item['hook_type']} | docs={item['doc_count']}")
    (output_dir / "knowledge-base.md").write_text("\n".join(overview_lines).rstrip() + "\n", encoding="utf-8")
    (output_dir / "video-index.json").write_text(json.dumps(video_summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def embed_query(text: str, config: Optional[RagConfig] = None) -> Tuple[List[float], str]:
    cfg = config or RagConfig()
    _, text_embedder, _, model_name = get_embedders(cfg)
    result = text_embedder.run(text=text)
    return result["embedding"], model_name


def retrieve_from_manifest(
    manifest: Dict[str, Any], query: str, top_k: int = 8, filters: Optional[Dict[str, Any]] = None, config: Optional[RagConfig] = None
) -> List[Dict[str, Any]]:
    cfg = config or RagConfig()
    bits = _import_haystack_bits()
    qdrant = manifest.get("qdrant") or {}
    collection_name = qdrant.get("collection_name")
    embedding_dim = int(qdrant.get("embedding_dim") or 0)
    if not collection_name or not embedding_dim:
        raise RuntimeError("Manifest is missing Qdrant collection metadata.")
    query_embedding, _ = embed_query(query, cfg)
    store = get_document_store(collection_name, embedding_dim=embedding_dim, recreate=False, config=cfg)
    retriever = bits["QdrantEmbeddingRetriever"](document_store=store)
    result = retriever.run(query_embedding=query_embedding, top_k=top_k, filters=filters)
    docs = result.get("documents") or result.get("document") or []
    out: List[Dict[str, Any]] = []
    for rank, doc in enumerate(docs, start=1):
        out.append(
            {
                "rank": rank,
                "content": getattr(doc, "content", ""),
                "meta": getattr(doc, "meta", {}) or {},
                "score": getattr(doc, "score", None),
                "id": getattr(doc, "id", None),
            }
        )
    return out


def build_rag_context(retrieved_docs: List[Dict[str, Any]], max_chars: int = 6000) -> str:
    parts: List[str] = []
    total = 0
    for item in retrieved_docs:
        meta = item.get("meta") or {}
        header = (
            f"[video_id={meta.get('video_id')} section={meta.get('section_title')} "
            f"archetype={meta.get('content_archetype')} hook={meta.get('hook_type')}]"
        )
        chunk = f"{header}\n{item.get('content', '').strip()}"
        total += len(chunk)
        if total > max_chars and parts:
            break
        parts.append(chunk)
    return "\n\n".join(parts)


def call_llm_json(system_prompt: str, user_prompt: str, config: Optional[RagConfig] = None) -> Dict[str, Any]:
    cfg = config or RagConfig()
    if not cfg.llm_available():
        raise RuntimeError("LLM configuration missing. Set OPENAI_MODEL/OPENAI_API_BASE or OPENCLAW_MODEL/OPENCLAW_API_BASE; API key may be omitted for no-auth compatible gateways.")
    bits = _import_haystack_bits()
    token = cfg.llm_api_key or os.getenv("OPENCLAW_DUMMY_API_KEY", "not-needed")
    secret = bits["Secret"].from_token(token)
    kwargs: Dict[str, Any] = {"api_key": secret, "model": cfg.llm_model}
    if cfg.llm_api_base:
        kwargs["api_base_url"] = cfg.llm_api_base
    generator = bits["OpenAIChatGenerator"](**kwargs)
    ChatMessage = bits["ChatMessage"]
    messages = [
        ChatMessage.from_system(f"{system_prompt}\nYou must respond with valid JSON only."),
        ChatMessage.from_user(user_prompt),
    ]
    reply = generator.run(messages=messages)["replies"][0].text
    try:
        return json.loads(reply)
    except Exception:
        match = re.search(r"\{.*\}", reply, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise RuntimeError(f"LLM did not return valid JSON: {reply[:500]}")


def default_script_output(manifest: Dict[str, Any], topic: str) -> Path:
    creator_slug = manifest.get("creator_slug") or "unknown-creator"
    out_dir = default_generated_script_dir(str(creator_slug))
    safe = slugify(topic)[:80] or "script"
    return out_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{safe}.json"
