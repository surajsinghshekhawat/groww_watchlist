"""Seed demo user, instruments, and default watchlist.

Demo credentials (development only):
  email:    demo@example.com
  password: DemoPass123!

Run: python -m app.seed
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.models import (
    Exchange,
    Instrument,
    TradingCategory,
    User,
    Watchlist,
    WatchlistItem,
    WatchlistSnapshot,
)
from app.db.session import AsyncSessionLocal

configure_logging()
logger = get_logger(__name__)

# Stable IDs so replay fixtures and docs can reference them.
DEMO_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DEMO_WATCHLIST_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

COMPANY_HDFC = uuid.UUID("11111111-1111-1111-1111-111111111101")
COMPANY_RELIANCE = uuid.UUID("11111111-1111-1111-1111-111111111102")
COMPANY_TCS = uuid.UUID("11111111-1111-1111-1111-111111111103")
COMPANY_INFY = uuid.UUID("11111111-1111-1111-1111-111111111104")
COMPANY_ICICI = uuid.UUID("11111111-1111-1111-1111-111111111105")
COMPANY_SBIN = uuid.UUID("11111111-1111-1111-1111-111111111106")
COMPANY_WIPRO = uuid.UUID("11111111-1111-1111-1111-111111111107")
COMPANY_LT = uuid.UUID("11111111-1111-1111-1111-111111111108")
COMPANY_NIFTY = uuid.UUID("11111111-1111-1111-1111-111111111190")
COMPANY_BANKNIFTY_SEC = uuid.UUID("11111111-1111-1111-1111-111111111191")

INSTRUMENT_IDS = {
    "HDFCBANK": uuid.UUID("22222222-2222-2222-2222-222222222201"),
    "RELIANCE": uuid.UUID("22222222-2222-2222-2222-222222222202"),
    "TCS": uuid.UUID("22222222-2222-2222-2222-222222222203"),
    "INFY": uuid.UUID("22222222-2222-2222-2222-222222222204"),
    "ICICIBANK": uuid.UUID("22222222-2222-2222-2222-222222222205"),
    "SBIN": uuid.UUID("22222222-2222-2222-2222-222222222206"),
    "WIPRO": uuid.UUID("22222222-2222-2222-2222-222222222207"),
    "LT": uuid.UUID("22222222-2222-2222-2222-222222222208"),
    "NIFTY50": uuid.UUID("22222222-2222-2222-2222-222222222290"),
    "NIFTYBANK": uuid.UUID("22222222-2222-2222-2222-222222222291"),
}


def _instruments() -> list[Instrument]:
    specs = [
        ("HDFCBANK", "HDFC Bank", COMPANY_HDFC, "Banking", "Private Banks", "1.05", "1.10", False),
        ("RELIANCE", "Reliance Industries", COMPANY_RELIANCE, "Energy", "Oil & Gas", "1.10", "1.05", False),
        ("TCS", "Tata Consultancy Services", COMPANY_TCS, "IT", "IT Services", "0.85", "0.95", False),
        ("INFY", "Infosys", COMPANY_INFY, "IT", "IT Services", "0.90", "1.00", False),
        ("ICICIBANK", "ICICI Bank", COMPANY_ICICI, "Banking", "Private Banks", "1.15", "1.05", False),
        ("SBIN", "State Bank of India", COMPANY_SBIN, "Banking", "PSU Banks", "1.20", "1.10", False),
        ("WIPRO", "Wipro", COMPANY_WIPRO, "IT", "IT Services", "0.95", "1.00", False),
        ("LT", "Larsen & Toubro", COMPANY_LT, "Industrials", "Construction", "1.05", "1.00", False),
        ("NIFTY50", "Nifty 50", COMPANY_NIFTY, "Index", "Benchmark", "1.00", "1.00", True),
        ("NIFTYBANK", "Nifty Bank", COMPANY_BANKNIFTY_SEC, "Banking", "Sector Index", "1.00", "1.00", True),
    ]
    rows: list[Instrument] = []
    for symbol, name, company_id, sector, industry, beta_m, beta_s, is_index in specs:
        rows.append(
            Instrument(
                instrument_id=INSTRUMENT_IDS[symbol],
                symbol=symbol,
                company_name=name,
                exchange=Exchange.NSE,
                company_id=company_id,
                sector=sector,
                industry=industry,
                beta_vs_market=Decimal(beta_m),
                beta_vs_sector=Decimal(beta_s),
                trading_category=TradingCategory.NORMAL,
                is_active=True,
                is_index=is_index,
            )
        )
    return rows


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # Always ensure instrument catalog is complete (idempotent adds).
        added_instruments = 0
        for row in _instruments():
            exists = await session.scalar(
                select(Instrument).where(Instrument.instrument_id == row.instrument_id)
            )
            if exists is None:
                session.add(row)
                added_instruments += 1

        existing = await session.scalar(select(User).where(User.user_id == DEMO_USER_ID))
        if existing:
            # Keep judge demo on MEDIUM so WORTH_WATCHING cards (TCS conflict beat) stay visible
            from app.db.models.user import Sensitivity

            if existing.sensitivity != Sensitivity.MEDIUM:
                existing.sensitivity = Sensitivity.MEDIUM
            await session.commit()
            logger.info(
                "seed_already_applied",
                extra={"new_instruments": added_instruments, "sensitivity_reset": "MEDIUM"},
            )
            return

        user = User(
            user_id=DEMO_USER_ID,
            email="demo@example.com",
            password_hash=hash_password("DemoPass123!"),
            display_name="Demo Trader",
            is_active=True,
        )
        session.add(user)

        watchlist = Watchlist(
            watchlist_id=DEMO_WATCHLIST_ID,
            user_id=DEMO_USER_ID,
            name="Morning Watch",
            version=1,
        )
        session.add(watchlist)

        demo_symbols = ["HDFCBANK", "RELIANCE", "TCS", "INFY", "ICICIBANK"]
        for symbol in demo_symbols:
            session.add(
                WatchlistItem(
                    watchlist_id=DEMO_WATCHLIST_ID,
                    instrument_id=INSTRUMENT_IDS[symbol],
                )
            )

        # Last checked ~10:00 IST demo day — novelty baseline for digest.
        last_checked = datetime(2026, 9, 4, 4, 30, tzinfo=timezone.utc)  # 10:00 IST
        for symbol in demo_symbols:
            session.add(
                WatchlistSnapshot(
                    user_id=DEMO_USER_ID,
                    instrument_id=INSTRUMENT_IDS[symbol],
                    last_checked_at=last_checked,
                    last_seen_price=None,
                    last_seen_event_states={},
                    version=1,
                )
            )

        await session.commit()
        logger.info(
            "seed_complete",
            extra={"user": "demo@example.com", "instruments": len(_instruments())},
        )


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
