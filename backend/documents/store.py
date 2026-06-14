"""Load, index, and search private local documents."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DOCS_DIR = Path(__file__).resolve().parents[2] / "private_docs"
INDEX_PATH = Path(__file__).resolve().parent / "index_cache.json"
CONFIDENCE_THRESHOLD = 0.45

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "can", "this", "that", "these", "those", "it", "its",
    "give", "me", "my", "show", "tell", "get", "list", "find", "please", "about",
    "all", "any", "our", "your", "their", "there", "here", "what", "which", "who",
    "how", "when", "where", "why", "some", "many", "much", "also", "just",
}


@dataclass
class DocumentChunk:
    chunk_id: str
    source: str
    text: str
    score: float
    search_method: str = "keyword"


@dataclass
class DocumentInfo:
    name: str
    size_bytes: int
    modified_at: str
    age_days: int
    freshness_label: str


def _stem(token: str) -> str:
    if len(token) <= 3:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 4:
        return token[:-1]
    return token


def _tokenize(text: str, *, strip_stopwords: bool = True) -> set[str]:
    raw = {token.lower() for token in re.findall(r"[a-zA-Z0-9_]+", text) if len(token) > 2}
    stemmed = {_stem(token) for token in raw}
    if not strip_stopwords:
        return stemmed
    return {token for token in stemmed if token not in STOP_WORDS and _stem(token) not in STOP_WORDS}


def _filename_tokens(filename: str) -> set[str]:
    stem = Path(filename).stem.replace("_", " ").replace("-", " ")
    return _tokenize(stem, strip_stopwords=False)


def _freshness_label(age_days: int) -> str:
    if age_days <= 1:
        return "Updated today"
    if age_days <= 7:
        return f"Updated {age_days} days ago"
    if age_days <= 30:
        return f"Updated {age_days} days ago"
    return f"Updated {age_days} days ago"


def get_document_info(name: str) -> DocumentInfo | None:
    path = DOCS_DIR / name
    if not path.is_file():
        return None
    stat = path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    age_days = max(0, (datetime.now(tz=timezone.utc) - modified).days)
    return DocumentInfo(
        name=name,
        size_bytes=stat.st_size,
        modified_at=modified.isoformat(),
        age_days=age_days,
        freshness_label=_freshness_label(age_days),
    )


def list_documents() -> list[str]:
    if not DOCS_DIR.exists():
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        return []
    return sorted(path.name for path in DOCS_DIR.glob("*") if path.is_file())


def list_documents_with_meta() -> list[dict[str, Any]]:
    return [
        asdict(info)
        for name in list_documents()
        if (info := get_document_info(name)) is not None
    ]


def _load_chunks() -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for path in sorted(DOCS_DIR.glob("*")):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            continue
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
        for index, paragraph in enumerate(paragraphs):
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{path.name}#{index}",
                    source=path.name,
                    text=paragraph,
                    score=0.0,
                )
            )
    return chunks


def _keyword_score(
    query_tokens: set[str],
    chunk_tokens: set[str],
    chunk_text: str,
    query: str,
    source: str,
) -> float:
    if not query_tokens:
        return 0.0

    overlap = len(query_tokens & chunk_tokens)
    base = overlap / len(query_tokens) if overlap else 0.0

    query_lower = query.lower()
    text_lower = chunk_text.lower()
    if query_lower in text_lower:
        base = min(1.0, base + 0.35)

    file_tokens = _filename_tokens(source)
    file_overlap = len(query_tokens & file_tokens)
    if file_overlap:
        file_score = file_overlap / len(query_tokens)
        base = max(base, file_score)
        if file_overlap >= 2 or file_score >= 0.5:
            base = min(1.0, base + 0.25)

    policy_markers = {"policy", "policies", "rule", "rules", "guideline", "handbook"}
    if query_tokens & policy_markers and "policy" in source.lower():
        base = min(1.0, max(base, 0.72))

    return base


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _semantic_scores(query: str, chunks: list[DocumentChunk]) -> dict[str, float]:
    try:
        from encoder.encoder_client import EncoderfileClient

        client = EncoderfileClient()
        model_type = client.model_info().get("model_type", "")
        if model_type != "embedding":
            return {}

        query_result = client.predict([query], normalize=True)
        query_emb = _extract_embedding(query_result)
        if not query_emb:
            return {}

        texts = [chunk.text for chunk in chunks]
        batch_result = client.predict(texts, normalize=True)
        results = batch_result.get("results", [])
        scores: dict[str, float] = {}
        for chunk, item in zip(chunks, results):
            emb = _extract_embedding({"results": [item]})
            if emb:
                scores[chunk.chunk_id] = max(0.0, _cosine_similarity(query_emb, emb))
        return scores
    except Exception:  # noqa: BLE001
        return {}


def _extract_embedding(result: dict[str, Any]) -> list[float] | None:
    results = result.get("results", [])
    if not results:
        return None
    first = results[0]
    embeddings = first.get("embeddings")
    if not embeddings:
        return None
    if isinstance(embeddings[0], list):
        vectors = embeddings
        if not vectors:
            return None
        dim = len(vectors[0])
        return [sum(row[i] for row in vectors) / len(vectors) for i in range(dim)]
    if isinstance(embeddings[0], (int, float)):
        return embeddings
    return None


def search_documents(query: str, limit: int = 4) -> list[DocumentChunk]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    chunks = _load_chunks()
    if not chunks:
        return []

    semantic = _semantic_scores(query, chunks)
    ranked: list[DocumentChunk] = []

    for chunk in chunks:
        chunk_tokens = _tokenize(chunk.text)
        keyword = _keyword_score(query_tokens, chunk_tokens, chunk.text, query, chunk.source)
        semantic_score = semantic.get(chunk.chunk_id, 0.0)
        if semantic_score > 0:
            score = 0.45 * keyword + 0.55 * semantic_score
            method = "hybrid"
        else:
            score = keyword
            method = "keyword"
        if score <= 0:
            continue
        ranked.append(
            DocumentChunk(
                chunk_id=chunk.chunk_id,
                source=chunk.source,
                text=chunk.text,
                score=min(1.0, score),
                search_method=method,
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)

    seen_sources: set[str] = set()
    deduped: list[DocumentChunk] = []
    for item in ranked:
        if item.source in seen_sources:
            continue
        seen_sources.add(item.source)
        deduped.append(item)

    return deduped[:limit]


def compute_confidence(matches: list[DocumentChunk]) -> int:
    if not matches:
        return 12
    top = matches[0].score
    support = min(len(matches), 4) / 4
    raw = (0.7 * top + 0.3 * support) * 100
    if top >= 0.65:
        raw = max(raw, 88)
    elif top >= 0.45:
        raw = max(raw, 72)
    return max(5, min(99, int(round(raw))))


def should_use_web(confidence: int, query: str, matches: list[DocumentChunk] | None = None) -> bool:
    lowered = query.lower()
    live_markers = (
        "latest",
        "news",
        "today",
        "current events",
        "recent",
        "this week",
        "this month",
        "2025",
        "2026",
    )
    if any(marker in lowered for marker in live_markers):
        return True

    if is_meta_followup_query(query):
        return True

    if compound_query_needs_web(query, matches):
        return True

    if matches and not should_trust_local_matches(query, matches):
        return True

    if matches:
        top_score = matches[0].score
        if top_score >= CONFIDENCE_THRESHOLD:
            return False
        if top_score >= 0.35 and confidence >= 50:
            return False

    return confidence < int(CONFIDENCE_THRESHOLD * 100)


def split_query_parts(query: str) -> list[str]:
    """Split multi-part questions on commas/semicolons; avoid breaking 'CSK and LSG' lists."""
    chunks = re.split(r"[,;?]+\s*", query.strip())
    parts: list[str] = []
    for chunk in chunks:
        piece = chunk.strip().rstrip("?")
        if piece:
            parts.append(piece)
    if len(parts) > 1:
        return parts

    if re.search(r"\s+and\s+", query, flags=re.IGNORECASE):
        subs = re.split(r"\s+and\s+", query, flags=re.IGNORECASE)
        independent = [s.strip() for s in subs if _looks_like_independent_question(s.strip())]
        if len(independent) >= 2:
            return independent

    return [query.strip()] if query.strip() else []


def _looks_like_independent_question(text: str) -> bool:
    lowered = text.lower().strip()
    if len(lowered.split()) < 3:
        return False
    return lowered.startswith(
        ("who ", "what ", "when ", "where ", "how ", "which ", "name ", "tell me ")
    )


def expand_meta_followup(query: str, prior_query: str | None) -> str:
    """Turn vague follow-ups like 'answer the other questions' into the missing sub-questions."""
    if not is_meta_followup_query(query) or not prior_query:
        return query
    parts = split_query_parts(prior_query)
    if len(parts) <= 1:
        return prior_query
    return ", ".join(parts[1:])


def is_meta_followup_query(query: str) -> bool:
    lowered = query.lower()
    meta_markers = (
        "other questions",
        "other parts",
        "other part",
        "what about the rest",
        "answer the other",
        "remaining questions",
        "rest of the question",
        "you missed",
        "you didn't answer",
    )
    return any(marker in lowered for marker in meta_markers)


def should_trust_local_matches(query: str, matches: list[DocumentChunk]) -> bool:
    """Reject keyword false positives (e.g. 'questions' matching company policy)."""
    if not matches:
        return False
    if is_meta_followup_query(query):
        return False
    if part_needs_web(query):
        return False

    query_tokens = _tokenize(query, strip_stopwords=True)
    if len(query_tokens) <= 2:
        return False

    top = matches[0]
    if top.score < 0.5:
        return False

    content_tokens = _tokenize(top.text, strip_stopwords=True)
    overlap = len(query_tokens & content_tokens)
    if overlap < max(2, len(query_tokens) // 2):
        return False

    return True


def is_compound_query(query: str) -> bool:
    return len(split_query_parts(query)) > 1


WEB_PART_MARKERS = (
    "who is",
    "who's",
    "what is the",
    "what's the",
    "ceo of",
    "ceo ",
    "president of",
    "president ",
    "prime minister",
    " pm of",
    " pm ",
    "minister of",
    "chief minister",
    " cm ",
    " cm?",
    "captain",
    "csk",
    "lsg",
    "ipl",
    "governor",
    "founder of",
    "founder ",
    "latest",
    "news",
    "when did",
    "where is",
    "how much",
    "price of",
    "current ",
    "today",
)


def part_needs_web(part: str) -> bool:
    lowered = part.lower()
    return any(marker in lowered for marker in WEB_PART_MARKERS)


def compound_query_needs_web(query: str, matches: list[DocumentChunk] | None = None) -> bool:
    """True when a multi-part question has at least one part that needs public web data."""
    parts = split_query_parts(query)
    if len(parts) <= 1:
        return False

    for part in parts:
        if part_needs_web(part):
            return True
        if matches:
            local_text = " ".join(match.text.lower() for match in matches)
            tokens = _tokenize(part, strip_stopwords=False)
            overlap = sum(1 for token in tokens if token in local_text)
            if overlap < max(1, len(tokens) // 3):
                return True
    return False


def pick_web_subquery(query: str, matches: list[DocumentChunk] | None = None) -> str:
    """Focus web search on the part of a compound question not answered locally."""
    parts = split_query_parts(query)
    if len(parts) <= 1:
        return query

    for part in parts:
        if part_needs_web(part):
            return part

    if matches:
        local_text = " ".join(match.text.lower() for match in matches)
        for part in parts:
            tokens = _tokenize(part, strip_stopwords=False)
            overlap = sum(1 for token in tokens if token in local_text)
            if overlap < max(1, len(tokens) // 3):
                return part

    return max(parts, key=len)


def is_live_data_query(query: str) -> bool:
    lowered = query.lower()
    time_markers = (
        "time in",
        "what time",
        "what is the time",
        "what's the time",
        "current time",
        "timezone",
        "convert time",
        "time is it",
        "what time is",
    )
    convert_markers = ("convert ", " to ", " in pst", " in est", " in utc", " in gmt")
    if any(marker in lowered for marker in time_markers):
        return True
    return "convert" in lowered and any(marker in lowered for marker in convert_markers)


def is_fetch_url_query(query: str) -> bool:
    lowered = query.lower()
    if "http://" in lowered or "https://" in lowered:
        return True
    fetch_markers = ("fetch url", "fetch the url", "fetch content", "read this page", "scrape")
    return any(marker in lowered for marker in fetch_markers)


def save_uploaded_file(filename: str, content: bytes) -> DocumentInfo:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name
    target = DOCS_DIR / safe_name
    target.write_bytes(content)
    info = get_document_info(safe_name)
    assert info is not None
    return info


def invalidate_index_cache() -> None:
    if INDEX_PATH.exists():
        INDEX_PATH.unlink(missing_ok=True)


def get_encoder_retrieval_status() -> dict[str, Any]:
    """Report how encoderfile participates in document retrieval."""
    try:
        from encoder.encoder_client import EncoderfileClient

        client = EncoderfileClient()
        if not client.health():
            return {
                "ok": False,
                "retrieval_mode": "keyword",
                "message": "Encoderfile offline — keyword search only",
            }
        info = client.model_info()
        model_type = info.get("model_type", "unknown")
        model_id = info.get("model_id") or info.get("name") or "encoderfile model"
        if model_type == "embedding":
            retrieval_mode = "semantic"
            message = "Encoderfile semantic embeddings active for document search"
        else:
            retrieval_mode = "keyword+filename"
            message = (
                f"Encoderfile online ({model_type}) — "
                "keyword + filename retrieval; swap to embedding model for vector search"
            )
        return {
            "ok": True,
            "model_type": model_type,
            "model_id": model_id,
            "base_url": client.base_url,
            "retrieval_mode": retrieval_mode,
            "message": message,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "retrieval_mode": "keyword",
            "message": f"Encoderfile unavailable: {exc}",
        }
