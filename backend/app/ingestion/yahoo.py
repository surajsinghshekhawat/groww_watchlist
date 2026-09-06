"""Yahoo Finance delayed quotes via yfinance (NSE .NS / index ^NSEI).

Free personal/demo path — not an official exchange feed. Label UI as Delayed · Yahoo.
Uses curl_cffi Chrome impersonation when available to reduce Yahoo 429s.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models import Instrument, PricePoint
from app.db.session import AsyncSessionLocal
from app.ingestion.base import RawObservation

logger = get_logger(__name__)

# Catalog symbol → Yahoo Finance ticker
_YAHOO_MAP: dict[str, str] = {
    "NIFTY50": "^NSEI",
    "NIFTYBANK": "^NSEBANK",
}

# In-process last-good quotes (survive transient Yahoo 429s)
_CACHE: dict[UUID, RawObservation] = {}
_SESSION = None
_LAST_FETCH_MONO = 0.0
_MIN_FETCH_GAP_S = 25.0


def yahoo_ticker_for(symbol: str, *, is_index: bool = False) -> str:
    sym = symbol.upper().strip()
    if sym in _YAHOO_MAP:
        return _YAHOO_MAP[sym]
    if is_index:
        return f"^{sym}"
    return f"{sym}.NS"


def _yf_session():
    """Shared session; prefer curl_cffi Chrome TLS fingerprint."""
    global _SESSION
    if _SESSION is not None:
        return _SESSION
    try:
        from curl_cffi import requests as curl_requests

        _SESSION = curl_requests.Session(impersonate="chrome")
        logger.info("yahoo_session", extra={"backend": "curl_cffi"})
    except Exception:  # noqa: BLE001
        import requests

        _SESSION = requests.Session()
        _SESSION.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
            }
        )
        logger.info("yahoo_session", extra={"backend": "requests"})
    return _SESSION


def _one_quote(ysym: str) -> tuple[Decimal, Decimal] | None:
    import yfinance as yf

    session = _yf_session()
    t = yf.Ticker(ysym, session=session)
    # Prefer short history — more reliable than .info under rate limits
    hist = t.history(period="5d", interval="1d", auto_adjust=True)
    if hist is not None and not hist.empty:
        last = hist.iloc[-1]
        price = Decimal(str(round(float(last["Close"]), 4)))
        vol = Decimal("0")
        if "Volume" in hist.columns:
            try:
                vol = Decimal(str(max(0, int(float(last["Volume"])))))
            except Exception:  # noqa: BLE001
                vol = Decimal("0")
        return price, vol
    fast = getattr(t, "fast_info", None)
    if fast is not None:
        lp = getattr(fast, "last_price", None)
        if lp is None and isinstance(fast, dict):
            lp = fast.get("last_price")
        if lp is not None:
            return Decimal(str(round(float(lp), 4))), Decimal("0")
    return None


def _fetch_snapshots_sync(
    rows: list[tuple[UUID, str, bool]],
) -> list[RawObservation]:
    global _LAST_FETCH_MONO
    now = datetime.now(timezone.utc)
    out: list[RawObservation] = []
    if not rows:
        return out

    # Soft throttle — engine may call every ~45s; refuse hammering Yahoo
    elapsed = time.monotonic() - _LAST_FETCH_MONO
    if _LAST_FETCH_MONO and elapsed < _MIN_FETCH_GAP_S * 0.4:
        # Too soon — serve cache only
        for iid, _, _ in rows:
            if iid in _CACHE:
                c = _CACHE[iid]
                out.append(
                    RawObservation(
                        instrument_id=c.instrument_id,
                        timestamp=now,
                        price=c.price,
                        volume=c.volume,
                        source="yahoo-cache",
                    )
                )
        return out

    _LAST_FETCH_MONO = time.monotonic()
    for i, (iid, sym, is_idx) in enumerate(rows):
        ysym = yahoo_ticker_for(sym, is_index=is_idx)
        try:
            pair = _one_quote(ysym)
            if pair is None:
                raise RuntimeError("empty")
            price, volume = pair
            obs = RawObservation(
                instrument_id=iid,
                timestamp=now,
                price=price,
                volume=volume,
                source="yahoo",
            )
            _CACHE[iid] = obs
            out.append(obs)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "yahoo_symbol_failed",
                extra={"symbol": sym, "yahoo": ysym, "error": type(exc).__name__},
            )
            if iid in _CACHE:
                c = _CACHE[iid]
                out.append(
                    RawObservation(
                        instrument_id=c.instrument_id,
                        timestamp=now,
                        price=c.price,
                        volume=c.volume,
                        source="yahoo-cache",
                    )
                )
        if i + 1 < len(rows):
            time.sleep(0.35)
    return out


class YahooFinanceMarketDataProvider:
    """Delayed NSE quotes via yfinance — production-shaped, demo-honest."""

    async def get_snapshot(self, instrument_ids: list[UUID]) -> list[RawObservation]:
        if not instrument_ids:
            return []
        async with AsyncSessionLocal() as session:
            rows = list(
                await session.scalars(
                    select(Instrument).where(Instrument.instrument_id.in_(instrument_ids))
                )
            )
        mapped = [(r.instrument_id, r.symbol, bool(r.is_index)) for r in rows]
        snaps = await asyncio.to_thread(_fetch_snapshots_sync, mapped)

        # DB fallback for any still-missing ids (last known price_point)
        have = {o.instrument_id for o in snaps}
        missing = [iid for iid in instrument_ids if iid not in have]
        if missing:
            async with AsyncSessionLocal() as session:
                for iid in missing:
                    pp = await session.scalar(
                        select(PricePoint)
                        .where(PricePoint.instrument_id == iid)
                        .order_by(PricePoint.timestamp.desc())
                        .limit(1)
                    )
                    if pp is None:
                        continue
                    snaps.append(
                        RawObservation(
                            instrument_id=iid,
                            timestamp=datetime.now(timezone.utc),
                            price=pp.price,
                            volume=pp.volume or Decimal("0"),
                            source="yahoo-db-fallback",
                        )
                    )
        return snaps

    async def get_history(
        self,
        instrument_id: UUID,
        *,
        start: datetime,
        end: datetime,
    ) -> list[RawObservation]:
        async with AsyncSessionLocal() as session:
            inst = await session.scalar(
                select(Instrument).where(Instrument.instrument_id == instrument_id)
            )
        if inst is None:
            return []

        def _hist() -> list[RawObservation]:
            import yfinance as yf

            ysym = yahoo_ticker_for(inst.symbol, is_index=bool(inst.is_index))
            t = yf.Ticker(ysym, session=_yf_session())
            frame = t.history(start=start.date(), end=end.date(), interval="1d", auto_adjust=True)
            out: list[RawObservation] = []
            if frame is None or frame.empty:
                return out
            for ts, row in frame.iterrows():
                try:
                    ts_aware = ts.to_pydatetime()
                    if ts_aware.tzinfo is None:
                        ts_aware = ts_aware.replace(tzinfo=timezone.utc)
                    else:
                        ts_aware = ts_aware.astimezone(timezone.utc)
                    close = float(row["Close"])
                    vol = (
                        float(row["Volume"])
                        if "Volume" in row and str(row["Volume"]) != "nan"
                        else 0.0
                    )
                    out.append(
                        RawObservation(
                            instrument_id=instrument_id,
                            timestamp=ts_aware,
                            price=Decimal(str(round(close, 4))),
                            volume=Decimal(str(max(0, int(vol)))),
                            source="yahoo",
                        )
                    )
                except Exception:  # noqa: BLE001
                    continue
            return out

        return await asyncio.to_thread(_hist)
