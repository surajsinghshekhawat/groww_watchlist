from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class InstrumentResponse(BaseModel):
    instrument_id: UUID
    symbol: str
    company_name: str
    exchange: str
    sector: str
    industry: str
    beta_vs_market: Decimal
    beta_vs_sector: Decimal
    trading_category: str
    is_index: bool

    model_config = {"from_attributes": True}


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class IntentWatchlistRequest(BaseModel):
    prompt: str = Field(min_length=8, max_length=800)


class IntentPreviewInstrument(BaseModel):
    instrument_id: UUID
    symbol: str
    company_name: str
    sector: str
    industry: str


class IntentPreviewResponse(BaseModel):
    proposed_name: str
    rationale: str
    model: str
    symbols_requested: list[str]
    sectors_requested: list[str]
    themes: list[str]
    matches: list[IntentPreviewInstrument]


class IntentCreateRequest(BaseModel):
    """Confirm a previewed plan into a brand-new watchlist (playlist)."""

    name: str = Field(min_length=1, max_length=120)
    instrument_ids: list[UUID] = Field(min_length=1, max_length=20)
    note: str | None = Field(default=None, max_length=400)
    prompt: str | None = Field(default=None, max_length=800)


class WatchlistUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    version: int = Field(ge=1)


class WatchlistItemResponse(BaseModel):
    instrument_id: UUID
    symbol: str
    company_name: str
    exchange: str
    sector: str
    note: str | None = None


class WatchlistResponse(BaseModel):
    watchlist_id: UUID
    name: str
    version: int
    updated_at: datetime
    instruments: list[WatchlistItemResponse] = []

    model_config = {"from_attributes": True}


class AddInstrumentRequest(BaseModel):
    instrument_id: UUID
    version: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=500)


class UpdateItemNoteRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)
    version: int = Field(ge=1)


class WatchlistPriceRow(BaseModel):
    instrument_id: UUID
    symbol: str
    company_name: str
    sector: str
    last_price: float | None
    prev_price: float | None
    change_pct: float | None
    volume: float | None
    as_of: datetime | None
    data_age_seconds: float | None
