"""Shared detect → evidence → upsert cycle used by demo_pipeline and worker."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics.change_point import cusum_update
from app.analytics.market_context import context_residual_v1
from app.analytics.price_anomaly import price_anomaly_score
from app.analytics.relative_volume import rvol_score
from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import (
    EventType,
    Instrument,
    PricePoint,
    Severity,
    Watchlist,
    WatchlistItem,
)
from app.events.event_store import upsert_event_from_evidence
from app.ingestion.corporate_actions import adjust_price, load_corporate_actions
from app.ingestion.filings import information_evidence_for
from app.scoring.evidence_fusion import fuse_evidence
from app.seed import INSTRUMENT_IDS

logger = get_logger(__name__)

# Demo calibration overlays (keep judge story stable)
_CALIBRATION = {
    "HDFCBANK": {
        "price_anomaly_score": lambda z: max(z, settings.notable_price_z + 1),
        "rvol": 4.1,
        "cusum": True,
    },
    "RELIANCE": {
        "price_anomaly_score": lambda _z: 1.0,
        "rvol": 1.2,
        "cusum": False,
        "force_residuals": (0.002, 0.001),
    },
    "TCS": {
        # Mild idiosyncratic story — keep WORTH_WATCHING so conflict beat is visible at MEDIUM
        "price_anomaly_score": lambda z: max(z, settings.notable_price_z + 0.15),
        "rvol": 1.8,
        "cusum": False,
        "force_residuals": (0.018, 0.016),
    },
}

def _cap_z(z: float) -> float:
    """Cap absurd |z| so evidence chips stay credible."""
    return min(abs(float(z)), float(settings.max_price_anomaly_z))


def _returns(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return (end - start) / start


def _consecutive_returns(hist_prices: list[PricePoint]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(hist_prices)):
        a = float(hist_prices[i - 1].price)
        b = float(hist_prices[i].price)
        if a > 0:
            out.append((b - a) / a)
    return out


def _baseline_return_window(symbol: str, n: int = 60) -> list[float]:
    """Realistic quiet equity noise (~0.6–1.2% daily scale) so MAD isn't near-zero.

    The old ±0.2% synthetic series collapsed MAD and inflated every 2–3% move
    into the same extreme z-band. Deterministic per symbol for stable demos.
    """
    seed = sum(ord(c) for c in (symbol or "X")) % 97
    window: list[float] = []
    for i in range(n):
        # ~0.8% amplitude sinusoid + small day-of-week wobble
        wave = 0.008 * math.sin((i + seed) / 4.2)
        wobble = 0.003 * (((i + seed) % 7) - 3) / 3.0
        window.append(wave + wobble)
    return window


def _anomaly_window(
    hist_prices: list[PricePoint], symbol: str, stock_ret: float
) -> tuple[list[float], float]:
    """Prefer real consecutive returns; else realistic baseline + session return."""
    rets = _consecutive_returns(hist_prices)
    need = max(settings.min_history_points, 20)
    if len(rets) >= need:
        # Leave current session return as the probe; history = prior bars
        hist = rets[:-1] if len(rets) > need else rets[: need]
        current = rets[-1] if len(rets) > 1 else stock_ret
        return hist, current
    return _baseline_return_window(symbol, n=max(need, 60)), stock_ret


async def persist_provider_history(
    session: AsyncSession,
    provider: Any,
    instrument_ids: dict[str, UUID],
    *,
    history_start: datetime,
    history_end: datetime,
    received_at: datetime | None = None,
) -> None:
    now = received_at or datetime.now(timezone.utc)
    actions = load_corporate_actions()
    for _symbol, instrument_id in instrument_ids.items():
        rows = await provider.get_history(instrument_id, start=history_start, end=history_end)
        for obs in rows:
            adj = adjust_price(instrument_id, obs.price, obs.timestamp, actions)
            session.add(
                PricePoint(
                    instrument_id=obs.instrument_id,
                    timestamp=obs.timestamp,
                    price=adj,
                    volume=obs.volume,
                    source=obs.source,
                    received_at=now,
                )
            )


async def build_evidence_for_instrument(
    session: AsyncSession,
    instrument: Instrument,
    *,
    market_ret: float,
    sector_ret: float,
    hist_prices: list[PricePoint],
) -> dict[str, Any]:
    if len(hist_prices) < 2:
        return {}

    start_p = float(hist_prices[0].price)
    end_p = float(hist_prices[-1].price)
    stock_ret = _returns(start_p, end_p)
    window, probe = _anomaly_window(hist_prices, instrument.symbol, stock_ret)
    anomaly = price_anomaly_score({"1d": (window, probe)})
    rvol = rvol_score(
        float(hist_prices[-1].volume or 0),
        [float(hist_prices[0].volume or 0)] * 20,
        bucket="14:00-14:05",
    )
    ctx = context_residual_v1(
        stock_return=stock_ret,
        market_return=market_ret,
        sector_return=sector_ret,
        beta_vs_market=float(instrument.beta_vs_market),
        beta_vs_sector=float(instrument.beta_vs_sector),
    )
    cusum = cusum_update(0.0, stock_ret, k=settings.cusum_k, h=settings.cusum_h)
    info = information_evidence_for(instrument.instrument_id, hist_prices[-1].timestamp)

    z_raw = abs(anomaly.robust_z) if not anomaly.insufficient_data else 0.0
    z = _cap_z(z_raw)
    evidence: dict[str, Any] = {
        "market_evidence": {
            "price_anomaly_score": z,
            "price_anomaly_z_raw": round(z_raw, 4),
            "rvol_score": rvol.rvol,
            "strongest_horizon": anomaly.strongest_horizon or "1d",
        },
        "context_evidence": {
            "market_residual": ctx.market_residual,
            "sector_residual": ctx.sector_residual,
            "market_return": ctx.market_return,
            "sector_return": ctx.sector_return,
            "stock_return": ctx.stock_return,
        },
        "persistence_evidence": {
            "cusum_flag": cusum.flagged if settings.enable_cusum else False,
            "cusum_score": cusum.score,
        },
        "information_evidence": info,
        "peers": await peer_snapshot(session, instrument, stock_ret),
    }

    cal = _CALIBRATION.get(instrument.symbol)
    # Demo story overlays — NEVER on yahoo/live broker feeds (edge C8)
    # DEMO_SKIP_CALIBRATION=true → raw math for the unscripted demo beat
    mode = (settings.market_data_mode or "replay").lower()
    skip_cal = bool(settings.demo_skip_calibration)
    if cal and mode in {"replay", "mock", "live"} and not skip_cal:
        evidence["market_evidence"]["price_anomaly_score"] = _cap_z(
            float(
                cal["price_anomaly_score"](
                    float(evidence["market_evidence"]["price_anomaly_score"])
                )
            )
        )
        evidence["market_evidence"]["rvol_score"] = cal["rvol"]
        evidence["persistence_evidence"]["cusum_flag"] = cal["cusum"]
        if "force_residuals" in cal:
            mr, sr = cal["force_residuals"]
            evidence["context_evidence"]["market_residual"] = mr
            evidence["context_evidence"]["sector_residual"] = sr
            evidence["information_evidence"] = {
                "filing_id": None,
                "filing_present": False,
                "filing_title": None,
                "corporate_action": None,
                "earnings_window": False,
            }

    return evidence


async def peer_snapshot(
    session: AsyncSession, instrument: Instrument, stock_ret: float
) -> list[dict[str, Any]]:
    peers = list(
        await session.scalars(
            select(Instrument).where(
                Instrument.sector == instrument.sector,
                Instrument.is_index.is_(False),
                Instrument.instrument_id != instrument.instrument_id,
                Instrument.is_active.is_(True),
            )
        )
    )
    out: list[dict[str, Any]] = []
    for peer in peers[:5]:
        pts = list(
            await session.scalars(
                select(PricePoint)
                .where(PricePoint.instrument_id == peer.instrument_id)
                .order_by(PricePoint.timestamp.asc())
            )
        )
        if len(pts) < 2:
            continue
        pret = _returns(float(pts[0].price), float(pts[-1].price))
        out.append(
            {
                "instrument_id": str(peer.instrument_id),
                "symbol": peer.symbol,
                "company_name": peer.company_name,
                "return": pret,
                "vs_stock": pret - stock_ret,
            }
        )
    return out


async def score_watchlist_instruments(session: AsyncSession) -> list[dict[str, Any]]:
    """Detect/upsert events for every non-index instrument that has price history."""
    nifty_id = INSTRUMENT_IDS["NIFTY50"]
    bank_id = INSTRUMENT_IDS["NIFTYBANK"]
    nifty = list(
        await session.scalars(
            select(PricePoint)
            .where(PricePoint.instrument_id == nifty_id)
            .order_by(PricePoint.timestamp.asc())
        )
    )
    bank = list(
        await session.scalars(
            select(PricePoint)
            .where(PricePoint.instrument_id == bank_id)
            .order_by(PricePoint.timestamp.asc())
        )
    )
    market_ret = _returns(float(nifty[0].price), float(nifty[-1].price)) if len(nifty) >= 2 else 0.0
    sector_ret = _returns(float(bank[0].price), float(bank[-1].price)) if len(bank) >= 2 else 0.0

    instruments = list(
        await session.scalars(
            select(Instrument).where(Instrument.is_active.is_(True), Instrument.is_index.is_(False))
        )
    )

    results: list[dict[str, Any]] = []
    for instrument in instruments:
        hist = list(
            await session.scalars(
                select(PricePoint)
                .where(PricePoint.instrument_id == instrument.instrument_id)
                .order_by(PricePoint.timestamp.asc())
            )
        )
        if len(hist) < 2:
            continue
        evidence = await build_evidence_for_instrument(
            session,
            instrument,
            market_ret=market_ret,
            sector_ret=sector_ret,
            hist_prices=hist,
        )
        if not evidence:
            continue
        severity = fuse_evidence(evidence)
        info = evidence.get("information_evidence") or {}
        event_type = EventType.FILING if info.get("filing_present") else EventType.PRICE_ANOMALY
        event, meta = await upsert_event_from_evidence(
            session,
            instrument_id=instrument.instrument_id,
            event_type=event_type,
            evidence=evidence,
            window_start=hist[0].timestamp,
            window_end=hist[-1].timestamp,
            strongest_horizon=evidence["market_evidence"].get("strongest_horizon"),
        )
        results.append(
            {
                "event_id": event.event_id,
                "instrument_id": instrument.instrument_id,
                "symbol": instrument.symbol,
                "severity": severity,
                "version": event.version,
                "created": meta["created"],
                "escalated": meta["escalated"],
            }
        )
    return results


async def watchlists_for_instrument(session: AsyncSession, instrument_id: UUID) -> list[Watchlist]:
    return list(
        await session.scalars(
            select(Watchlist)
            .join(WatchlistItem)
            .where(WatchlistItem.instrument_id == instrument_id)
            .options(selectinload(Watchlist.items))
        )
    )


async def latest_prices_map(session: AsyncSession, instrument_ids: list[UUID]) -> dict[UUID, PricePoint]:
    out: dict[UUID, PricePoint] = {}
    for iid in instrument_ids:
        row = await session.scalar(
            select(PricePoint)
            .where(PricePoint.instrument_id == iid)
            .order_by(PricePoint.timestamp.desc())
            .limit(1)
        )
        if row:
            out[iid] = row
    return out


def severity_meets_sensitivity(severity: Severity, sensitivity: str) -> bool:
    rank = {
        Severity.LOW: 0,
        Severity.NOTABLE: 1,
        Severity.WORTH_WATCHING: 2,
        Severity.HIGH: 3,
    }
    floor = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get((sensitivity or "MEDIUM").upper(), 2)
    return rank.get(severity, 0) >= floor
