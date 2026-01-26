import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document


@dataclass(frozen=True)
class RetrieverConfig:
    chroma_dir: str
    collection_name: str = "ecom_policies"
    embed_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"

    # Pull more candidates, then filter + rerank
    k: int = 8

    # Chroma returns a distance-like score here (lower is better).
    # Tune this based on your observed scores.
    score_threshold: float = 0.76

    # Cap returned chunks (keep context clean for the LLM)
    max_results: int = 2

    # Optional: route to a specific policy file when intent is obvious
    enable_routing: bool = True


def load_retriever_config_from_env() -> RetrieverConfig:
    load_dotenv()
    return RetrieverConfig(
        chroma_dir=os.getenv("CHROMA_DIR", "app/storage/chroma"),
        collection_name=os.getenv("CHROMA_COLLECTION", "ecom_policies"),
        embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    )


def get_vectorstore(cfg: Optional[RetrieverConfig] = None) -> Chroma:
    cfg = cfg or load_retriever_config_from_env()

    embeddings = OllamaEmbeddings(
        model=cfg.embed_model,
        base_url=cfg.ollama_base_url,
    )

    return Chroma(
        persist_directory=cfg.chroma_dir,
        collection_name=cfg.collection_name,
        embedding_function=embeddings,
    )


def _route_source_filter(query: str) -> Optional[str]:
    """
    Very simple rule-based router.
    Returns a regex to match Document.metadata['source'] if we want to restrict.
    """
    q = query.lower()

    # Warranty-related queries
    if any(k in q for k in ["warranty", "defect", "manufacturing", "photo", "pilling", "zipper", "seam"]):
        return r"warranty\.md$"

    # Shipping / delivery related
    if any(k in q for k in ["lost", "in transit", "label created", "delivered but missing", "carrier"]):
        return r"shipping_sla\.md$"

    # Returns related
    if any(k in q for k in ["return", "exchange", "doesn't fit", "changed mind", "buyer remorse"]):
        return r"returns\.md$"

    # Refund/compensation related
    if any(k in q for k in ["refund", "store credit", "gift", "restocking", "shipping fee", "inspection"]):
        return r"refunds\.md$"

    return None


def similarity_search_with_scores(
    query: str,
    *,
    cfg: Optional[RetrieverConfig] = None,
) -> List[Tuple[Document, float]]:
    cfg = cfg or load_retriever_config_from_env()
    db = get_vectorstore(cfg)
    return db.similarity_search_with_score(query, k=cfg.k)


def _load_policy_docs_from_fs(policies_dir: str) -> List[Document]:
    base = Path(policies_dir)
    if not base.exists():
        return []
    docs: List[Document] = []
    for path in base.glob("**/*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        docs.append(Document(page_content=text, metadata={"source": path.name}))
    return docs


def _fallback_retrieve_policy_chunks(query: str, *, cfg: RetrieverConfig) -> List[Document]:
    docs = _load_policy_docs_from_fs(os.getenv("POLICIES_DIR", "app/policies"))
    if not docs:
        return []

    q = query.lower()
    terms = [t for t in re.split(r"\W+", q) if len(t) > 3]

    def score(doc: Document) -> float:
        text = (doc.page_content or "").lower()
        hits = sum(text.count(t) for t in terms) or 0
        # lower is better to match existing distance semantics
        return 1.0 / (1 + hits)

    ranked = sorted(docs, key=score)
    return ranked[: cfg.max_results]


def _rerank_for_query(query: str, doc: Document, distance: float) -> float:
    """
    Produce a 'better is lower' score by adjusting the distance with simple lexical hints.
    This helps when embeddings return multiple warranty chunks that are all close.

    We keep it deterministic and cheap.
    """
    text = (doc.page_content or "").lower()
    q = query.lower()

    bonus = 0.0

    # If the question is about photos/evidence, prefer chunks containing those words
    if "photo" in q or "evidence" in q or "proof" in q:
        if "photo" in text:
            bonus -= 0.08
        if "evidence" in text or "verification" in text:
            bonus -= 0.04
        if "exclusion" in text or "invalid" in text:
            bonus += 0.03  # slightly de-prioritize exclusions for evidence questions

    # Small general preference for chunks that include "must" / "require"
    if "require" in text or "must" in text:
        bonus -= 0.01

    return distance + bonus


def retrieve_policy_chunks_strict(
    query: str,
    *,
    cfg: Optional[RetrieverConfig] = None,
) -> List[Document]:
    cfg = cfg or load_retriever_config_from_env()
    try:
        results = similarity_search_with_scores(query, cfg=cfg)
    except Exception:
        # Fallback to filesystem policy retrieval when embeddings are unavailable
        return _fallback_retrieve_policy_chunks(query, cfg=cfg)

    # Optional routing: filter candidates to a specific policy file.
    if cfg.enable_routing:
        pattern = _route_source_filter(query)
        if pattern:
            rx = re.compile(pattern, re.IGNORECASE)
            results = [(d, s) for (d, s) in results if rx.search(str(d.metadata.get("source", "")))]

    # Score threshold filter (distance <= threshold)
    filtered = [(d, s) for (d, s) in results if s <= cfg.score_threshold]

    # Fallback: never return empty, take best 1–2 from whatever we have
    if not filtered:
        filtered = results[: min(2, len(results))]

    # Rerank using lexical hints
    reranked = sorted(filtered, key=lambda pair: _rerank_for_query(query, pair[0], pair[1]))

    return [d for (d, _s) in reranked[: cfg.max_results]]