from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DigestInstrument(BaseModel):
    instrument_id: UUID
    symbol: str
    company_name: str


class RetrievalChip(BaseModel):
    source: str
    title: str
    origin: str
    score: float | None = None


class DigestItem(BaseModel):
    event_id: UUID
    instrument: DigestInstrument
    severity: str
    status: str
    tier: str
    attention_score: float
    significance: float
    novelty: float
    confidence: float
    confidence_breakdown: str | None = None
    explanation: str
    evidence: dict[str, Any]
    peers: list[dict[str, Any]] = Field(default_factory=list)
    retrieval: list[RetrievalChip] = Field(default_factory=list)
    user_note: str | None = None
    user_feedback: str | None = None
    version: int
    detected_at: datetime
    data_conflict: bool = False
    data_age_seconds: float | None = None


class IgnoredItem(BaseModel):
    instrument_id: UUID
    symbol: str
    company_name: str
    reason: str
    detail: str | None = None


class DigestSummary(BaseModel):
    high_attention: int
    worth_watching: int
    notable: int
    hidden_high: int = 0
    ignored_count: int = 0
    empty_hint: str | None = None
    # One-line executive pitch for the Attention header
    headline: str | None = None


class DigestResponse(BaseModel):
    generated_at: datetime
    last_checked_at: datetime | None
    watchlist_id: UUID
    items: list[DigestItem]
    ignored: list[IgnoredItem] = Field(default_factory=list)
    summary: DigestSummary
    market_data_mode: str
    data_age_seconds: float | None = None
    # Novelty is per (user, instrument), shared across watchlists (edge F2 — v1)
    novelty_scope: str = "user_instrument"


class MarkSeenItem(BaseModel):
    event_id: UUID
    severity_seen: str
    event_version: int = Field(ge=1)


class MarkSeenRequest(BaseModel):
    items: list[MarkSeenItem] = Field(min_length=1, max_length=50)
