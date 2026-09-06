from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.db.models import PricePoint, Watchlist, WatchlistItem
from app.repositories.watchlists import InstrumentRepository, WatchlistRepository
from app.schemas.watchlist import (
    AddInstrumentRequest,
    InstrumentResponse,
    UpdateItemNoteRequest,
    WatchlistCreate,
    WatchlistItemResponse,
    WatchlistPriceRow,
    WatchlistResponse,
    WatchlistUpdate,
)


def serialize_watchlist(watchlist: Watchlist) -> WatchlistResponse:
    instruments = []
    for item in watchlist.items:
        inst = item.instrument
        instruments.append(
            WatchlistItemResponse(
                instrument_id=inst.instrument_id,
                symbol=inst.symbol,
                company_name=inst.company_name,
                exchange=inst.exchange.value if hasattr(inst.exchange, "value") else str(inst.exchange),
                sector=inst.sector,
                note=getattr(item, "note", None),
            )
        )
    return WatchlistResponse(
        watchlist_id=watchlist.watchlist_id,
        name=watchlist.name,
        version=watchlist.version,
        updated_at=watchlist.updated_at,
        instruments=instruments,
    )


class WatchlistService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.watchlists = WatchlistRepository(session)
        self.instruments = InstrumentRepository(session)

    async def list_mine(self, user_id: UUID) -> list[WatchlistResponse]:
        rows = await self.watchlists.list_for_user(user_id)
        return [serialize_watchlist(w) for w in rows]

    async def create(self, user_id: UUID, payload: WatchlistCreate) -> WatchlistResponse:
        watchlist = await self.watchlists.create(user_id=user_id, name=payload.name)
        await self.session.commit()
        loaded = await self.watchlists.get_owned(watchlist.watchlist_id, user_id)
        assert loaded is not None
        return serialize_watchlist(loaded)

    async def get(self, user_id: UUID, watchlist_id: UUID) -> WatchlistResponse:
        watchlist = await self._owned_or_404(user_id, watchlist_id)
        return serialize_watchlist(watchlist)

    async def update(
        self, user_id: UUID, watchlist_id: UUID, payload: WatchlistUpdate
    ) -> WatchlistResponse:
        watchlist = await self._owned_or_404(user_id, watchlist_id)
        self._assert_version(watchlist, payload.version)
        if payload.name is not None:
            watchlist.name = payload.name
        watchlist.version += 1
        await self.session.commit()
        loaded = await self.watchlists.get_owned(watchlist_id, user_id)
        assert loaded is not None
        return serialize_watchlist(loaded)

    async def delete(self, user_id: UUID, watchlist_id: UUID) -> None:
        watchlist = await self._owned_or_404(user_id, watchlist_id)
        await self.session.delete(watchlist)
        await self.session.commit()

    async def add_instrument(
        self, user_id: UUID, watchlist_id: UUID, payload: AddInstrumentRequest
    ) -> WatchlistResponse:
        watchlist = await self._owned_or_404(user_id, watchlist_id)
        self._assert_version(watchlist, payload.version)

        instrument = await self.instruments.get_by_id(payload.instrument_id)
        if instrument is None or not instrument.is_active:
            raise AppError("INSTRUMENT_NOT_FOUND", "Instrument not found", 404)

        count = await self.watchlists.count_items(watchlist_id)
        existing_ids = {item.instrument_id for item in watchlist.items}
        if payload.instrument_id not in existing_ids and count >= settings.max_watchlist_size:
            raise AppError(
                "WATCHLIST_LIMIT_REACHED",
                f"Watchlist may contain at most {settings.max_watchlist_size} instruments",
                422,
            )

        await self.watchlists.add_item(
            watchlist=watchlist,
            instrument_id=payload.instrument_id,
            note=payload.note,
        )
        await self.session.commit()
        loaded = await self.watchlists.get_owned(watchlist_id, user_id)
        assert loaded is not None
        return serialize_watchlist(loaded)

    async def remove_instrument(
        self, user_id: UUID, watchlist_id: UUID, instrument_id: UUID, *, version: int
    ) -> WatchlistResponse:
        watchlist = await self._owned_or_404(user_id, watchlist_id)
        self._assert_version(watchlist, version)
        removed = await self.watchlists.remove_item(
            watchlist=watchlist, instrument_id=instrument_id
        )
        if not removed:
            raise AppError("INSTRUMENT_NOT_IN_WATCHLIST", "Instrument not in watchlist", 404)
        await self.session.commit()
        loaded = await self.watchlists.get_owned(watchlist_id, user_id)
        assert loaded is not None
        return serialize_watchlist(loaded)

    async def update_item_note(
        self,
        user_id: UUID,
        watchlist_id: UUID,
        instrument_id: UUID,
        payload: UpdateItemNoteRequest,
    ) -> WatchlistResponse:
        watchlist = await self._owned_or_404(user_id, watchlist_id)
        self._assert_version(watchlist, payload.version)
        item = await self.session.scalar(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist_id,
                WatchlistItem.instrument_id == instrument_id,
            )
        )
        if item is None:
            raise AppError("INSTRUMENT_NOT_IN_WATCHLIST", "Instrument not in watchlist", 404)
        item.note = payload.note
        watchlist.version += 1
        await self.session.commit()
        loaded = await self.watchlists.get_owned(watchlist_id, user_id)
        assert loaded is not None
        return serialize_watchlist(loaded)

    async def search_instruments(self, q: str, limit: int = 20) -> list[InstrumentResponse]:
        if len(q.strip()) < 1:
            raise AppError("INVALID_QUERY", "Search query is required", 422)
        limit = max(1, min(limit, 50))
        rows = await self.instruments.search(q, limit=limit)
        return [
            InstrumentResponse(
                instrument_id=r.instrument_id,
                symbol=r.symbol,
                company_name=r.company_name,
                exchange=r.exchange.value if hasattr(r.exchange, "value") else str(r.exchange),
                sector=r.sector,
                industry=r.industry,
                beta_vs_market=r.beta_vs_market,
                beta_vs_sector=r.beta_vs_sector,
                trading_category=r.trading_category.value
                if hasattr(r.trading_category, "value")
                else str(r.trading_category),
                is_index=r.is_index,
            )
            for r in rows
        ]

    async def price_rows(self, user_id: UUID, watchlist_id: UUID) -> list[WatchlistPriceRow]:
        watchlist = await self._owned_or_404(user_id, watchlist_id)
        now = datetime.now(timezone.utc)
        rows: list[WatchlistPriceRow] = []
        for item in watchlist.items:
            inst = item.instrument
            pts = list(
                await self.session.scalars(
                    select(PricePoint)
                    .where(PricePoint.instrument_id == inst.instrument_id)
                    .order_by(PricePoint.timestamp.desc())
                    .limit(120)
                )
            )
            last = pts[0] if pts else None
            # Session / window open ≈ oldest point in the recent buffer (not micro-tick)
            session_open = pts[-1] if pts else None
            change = None
            if last and session_open and float(session_open.price) != 0:
                change = (
                    (float(last.price) - float(session_open.price))
                    / float(session_open.price)
                    * 100.0
                )
            age = (now - last.received_at).total_seconds() if last else None
            rows.append(
                WatchlistPriceRow(
                    instrument_id=inst.instrument_id,
                    symbol=inst.symbol,
                    company_name=inst.company_name,
                    sector=inst.sector,
                    last_price=float(last.price) if last else None,
                    prev_price=float(session_open.price) if session_open else None,
                    change_pct=round(change, 3) if change is not None else None,
                    volume=float(last.volume) if last and last.volume is not None else None,
                    as_of=last.timestamp if last else None,
                    data_age_seconds=round(age, 1) if age is not None else None,
                )
            )
        return rows

    async def _owned_or_404(self, user_id: UUID, watchlist_id: UUID) -> Watchlist:
        # Ownership check — return 404 (not 403) to avoid leaking existence.
        watchlist = await self.watchlists.get_owned(watchlist_id, user_id)
        if watchlist is None:
            raise AppError("WATCHLIST_NOT_FOUND", "Watchlist not found", 404)
        return watchlist

    @staticmethod
    def _assert_version(watchlist: Watchlist, expected: int) -> None:
        if watchlist.version != expected:
            raise AppError(
                "VERSION_CONFLICT",
                "Watchlist was updated on another device. Refresh and retry.",
                409,
                details={"current_version": watchlist.version},
            )
