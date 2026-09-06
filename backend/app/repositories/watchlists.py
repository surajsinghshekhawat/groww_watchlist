from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Instrument, Watchlist, WatchlistItem


class InstrumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, instrument_id: UUID) -> Instrument | None:
        return await self.session.scalar(
            select(Instrument).where(Instrument.instrument_id == instrument_id)
        )

    async def search(self, q: str, *, limit: int = 20) -> list[Instrument]:
        pattern = f"%{q.strip()}%"
        stmt = (
            select(Instrument)
            .where(
                Instrument.is_active.is_(True),
                or_(
                    Instrument.symbol.ilike(pattern),
                    Instrument.company_name.ilike(pattern),
                ),
            )
            .order_by(Instrument.symbol)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result)


class WatchlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: UUID) -> list[Watchlist]:
        stmt = (
            select(Watchlist)
            .where(Watchlist.user_id == user_id)
            .options(selectinload(Watchlist.items).selectinload(WatchlistItem.instrument))
            .order_by(Watchlist.updated_at.desc())
        )
        return list(await self.session.scalars(stmt))

    async def get_owned(self, watchlist_id: UUID, user_id: UUID) -> Watchlist | None:
        stmt = (
            select(Watchlist)
            .where(Watchlist.watchlist_id == watchlist_id, Watchlist.user_id == user_id)
            .options(selectinload(Watchlist.items).selectinload(WatchlistItem.instrument))
        )
        return await self.session.scalar(stmt)

    async def create(self, *, user_id: UUID, name: str) -> Watchlist:
        watchlist = Watchlist(user_id=user_id, name=name, version=1)
        self.session.add(watchlist)
        await self.session.flush()
        return watchlist

    async def count_items(self, watchlist_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(WatchlistItem)
                .where(WatchlistItem.watchlist_id == watchlist_id)
            )
            or 0
        )

    async def add_item(
        self, *, watchlist: Watchlist, instrument_id: UUID, note: str | None = None
    ) -> WatchlistItem | None:
        existing = await self.session.scalar(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist.watchlist_id,
                WatchlistItem.instrument_id == instrument_id,
            )
        )
        if existing:
            if note is not None:
                existing.note = note
                watchlist.version += 1
                await self.session.flush()
            return existing
        item = WatchlistItem(
            watchlist_id=watchlist.watchlist_id,
            instrument_id=instrument_id,
            note=note,
        )
        self.session.add(item)
        watchlist.version += 1
        await self.session.flush()
        return item

    async def remove_item(self, *, watchlist: Watchlist, instrument_id: UUID) -> bool:
        result = await self.session.execute(
            delete(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist.watchlist_id,
                WatchlistItem.instrument_id == instrument_id,
            )
        )
        if result.rowcount:
            watchlist.version += 1
            await self.session.flush()
            return True
        return False
