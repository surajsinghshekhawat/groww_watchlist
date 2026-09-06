"""BM25-ish keyword RAG over local filing docs + optional web snippets."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.paths import filings_docs_dir

logger = get_logger(__name__)

_TOKEN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RetrievedChunk:
    source: str
    title: str
    text: str
    score: float
    origin: str  # document | web


def _docs_dir() -> Path:
    return filings_docs_dir()


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _load_documents() -> list[tuple[str, str, str]]:
    """Return (path_name, title, body)."""
    root = _docs_dir()
    if not root.exists():
        return []
    out: list[tuple[str, str, str]] = []
    for path in sorted(root.glob("*.md")):
        body = path.read_text(encoding="utf-8")
        title = path.stem
        for line in body.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        out.append((path.name, title, body))
    return out


def _score_doc(query_tokens: list[str], doc_tokens: list[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    df: dict[str, int] = {}
    for t in set(doc_tokens):
        df[t] = doc_tokens.count(t)
    score = 0.0
    doc_len = len(doc_tokens)
    avgdl = max(doc_len, 1)
    for qt in query_tokens:
        f = df.get(qt, 0)
        if f == 0:
            continue
        idf = math.log(1 + 1.5)
        score += idf * (f * 2.2) / (f + 1.2 * (0.25 + 0.75 * doc_len / avgdl))
    return score


def retrieve_documents(query: str, *, top_k: int = 3) -> list[RetrievedChunk]:
    q_tokens = _tokenize(query)
    scored: list[RetrievedChunk] = []
    for name, title, body in _load_documents():
        parts = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        for i, part in enumerate(parts):
            s = _score_doc(q_tokens, _tokenize(part + " " + title + " " + name))
            if s <= 0:
                continue
            scored.append(
                RetrievedChunk(
                    source=f"{name}#p{i}",
                    title=title,
                    text=part[:1200],
                    score=s,
                    origin="document",
                )
            )
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:top_k]


async def retrieve_web(query: str, *, top_k: int = 2) -> list[RetrievedChunk]:
    if not settings.enable_web_retrieval:
        return []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            if res.status_code != 200:
                return []
            data = res.json()
            chunks: list[RetrievedChunk] = []
            abstract = (data.get("AbstractText") or "").strip()
            if abstract:
                chunks.append(
                    RetrievedChunk(
                        source=data.get("AbstractURL") or "duckduckgo",
                        title=data.get("Heading") or query,
                        text=abstract[:1200],
                        score=1.0,
                        origin="web",
                    )
                )
            for topic in (data.get("RelatedTopics") or [])[:top_k]:
                if isinstance(topic, dict) and topic.get("Text"):
                    chunks.append(
                        RetrievedChunk(
                            source=topic.get("FirstURL") or "duckduckgo-related",
                            title=query,
                            text=str(topic["Text"])[:800],
                            score=0.5,
                            origin="web",
                        )
                    )
            return chunks[:top_k]
    except Exception as exc:  # noqa: BLE001
        logger.warning("web_retrieval_failed", extra={"error": type(exc).__name__})
        return []


async def retrieve_for_symbol(
    symbol: str,
    evidence: dict,
    *,
    include_web: bool = False,
) -> list[RetrievedChunk]:
    """Retrieve only symbol-relevant docs — never attach another ticker's filing."""
    sym = symbol.upper()
    filing = (evidence.get("information_evidence") or {}).get("filing_id") or ""
    query = f"{sym} {filing} filing stock session residual volume"

    all_hits = retrieve_documents(query, top_k=12)
    matched = [
        c
        for c in all_hits
        if sym in c.source.upper() or sym in c.title.upper() or sym in c.text[:400].upper()
    ]
    matched.sort(key=lambda c: (0 if sym in c.source.upper() else 1, -c.score))

    if not matched:
        for name, title, body in _load_documents():
            if name.upper().startswith(sym):
                matched.append(
                    RetrievedChunk(
                        source=f"{name}#0",
                        title=title,
                        text=body[:1200],
                        score=1.0,
                        origin="document",
                    )
                )
                break

    if not include_web:
        # Dedupe by title so paragraph splits don't spam identical chips
        deduped: list[RetrievedChunk] = []
        seen_titles: set[str] = set()
        for c in matched:
            key = c.title.strip().lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            deduped.append(c)
        return deduped[:2]

    web: list[RetrievedChunk] = []
    try:
        import asyncio

        web = await asyncio.wait_for(retrieve_web(f"{sym} NSE stock", top_k=1), timeout=3.0)
        web = [w for w in web if sym in w.text.upper() or sym in w.title.upper()]
    except Exception:  # noqa: BLE001
        web = []
    return (matched[:3] + web)[:4]
