from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import settings
from app.core.exceptions import AppError
from app.db.models import (
    EventStatus,
    MarketEvent,
    PricePoint,
    Severity,
    User,
    WatchlistSnapshot,
)
from app.explanation.llm import ExplanationResult, explain_with_optional_llm
from app.explanation.rag import retrieve_for_symbol
from app.explanation.templates import explanation_from_evidence
from app.repositories.watchlists import WatchlistRepository
from app.schemas.digest import (
    DigestInstrument,
    DigestItem,
    DigestResponse,
    DigestSummary,
    IgnoredItem,
    MarkSeenRequest,
    RetrievalChip,
)
from app.scoring.attention import attention_score, ui_tier
from app.scoring.confidence import confidence_score
from app.scoring.novelty import novelty_score
from app.scoring.significance import significance_continuous
from app.services.pipeline import severity_meets_sensitivity
from app.services import notification_service as notif_svc
from app.services.feedback_service import feedback_by_events


def _digest_headline(
    items: list[DigestItem],
    *,
    ignored_count: int,
    high: int,
    watch: int,
    notable: int,
) -> str:
    """Elevator-pitch sentence for the Attention header."""
    if not items and ignored_count:
        return (
            f"Today: nothing novel enough for the digest — "
            f"{ignored_count} name(s) explained under What we ignored."
        )
    if not items:
        return "Today: no novel attention items right now."

    bits: list[str] = []
    highs = [i for i in items if i.tier == "HIGH_ATTENTION"]
    if high:
        names = ", ".join(i.instrument.company_name for i in highs[:2])
        if high > 2:
            names = f"{names} +"
        bits.append(f"{high} High-attention move{'s' if high != 1 else ''} ({names})")
    if watch:
        bits.append(f"{watch} worth watching")
    if notable:
        bits.append(f"{notable} notable")
    core = ", ".join(bits) if bits else "a short digest"
    noise = (
        f", {ignored_count} filtered as noise"
        if ignored_count
        else ", everything else was noise"
    )
    return f"Today: {core}{noise}."


class DigestService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.watchlists = WatchlistRepository(session)

    async def get_digest(self, user_id: UUID, watchlist_id: UUID, top_k: int | None = None) -> DigestResponse:
        top_k = top_k or settings.top_k
        top_k = max(1, min(top_k, 20))

        watchlist = await self.watchlists.get_owned(watchlist_id, user_id)
        if watchlist is None:
            raise AppError("WATCHLIST_NOT_FOUND", "Watchlist not found", 404)

        user = await self.session.scalar(select(User).where(User.user_id == user_id))
        sens = "MEDIUM"
        if user is not None and getattr(user, "sensitivity", None) is not None:
            sens = user.sensitivity.value if hasattr(user.sensitivity, "value") else str(user.sensitivity)

        note_by_inst = {
            item.instrument_id: getattr(item, "note", None) for item in watchlist.items
        }
        instrument_ids = [item.instrument_id for item in watchlist.items]
        if not instrument_ids:
            return DigestResponse(
                generated_at=datetime.now(timezone.utc),
                last_checked_at=None,
                watchlist_id=watchlist_id,
                items=[],
                ignored=[],
                summary=DigestSummary(
                    high_attention=0,
                    worth_watching=0,
                    notable=0,
                    empty_hint="Add instruments or describe a watchlist to start scoring.",
                    headline="Today: add instruments to start scoring.",
                ),
                market_data_mode=settings.market_data_mode,
                novelty_scope="user_instrument",
            )

        snapshots = list(
            await self.session.scalars(
                select(WatchlistSnapshot).where(
                    WatchlistSnapshot.user_id == user_id,
                    WatchlistSnapshot.instrument_id.in_(instrument_ids),
                )
            )
        )
        snap_by_inst = {s.instrument_id: s for s in snapshots}
        # Display the most recent time the user actually engaged — never the oldest seed date
        last_checked = max((s.last_checked_at for s in snapshots), default=None)

        events = list(
            await self.session.scalars(
                select(MarketEvent)
                .where(
                    MarketEvent.instrument_id.in_(instrument_ids),
                    MarketEvent.status.in_([EventStatus.OPEN, EventStatus.ESCALATED]),
                )
                .options(
                    selectinload(MarketEvent.evidence),
                    selectinload(MarketEvent.instrument),
                )
            )
        )
        # One open story per instrument — keep highest severity, then newest
        _sev_rank = {
            Severity.LOW: 0,
            Severity.NOTABLE: 1,
            Severity.WORTH_WATCHING: 2,
            Severity.HIGH: 3,
        }
        best_by_inst: dict[UUID, MarketEvent] = {}
        for event in events:
            prev = best_by_inst.get(event.instrument_id)
            if prev is None:
                best_by_inst[event.instrument_id] = event
                continue
            if _sev_rank[event.severity] > _sev_rank[prev.severity]:
                best_by_inst[event.instrument_id] = event
            elif (
                _sev_rank[event.severity] == _sev_rank[prev.severity]
                and event.detected_at >= prev.detected_at
            ):
                best_by_inst[event.instrument_id] = event
        events = list(best_by_inst.values())
        fb_map = await feedback_by_events(
            self.session,
            user_id=user_id,
            event_ids=[e.event_id for e in events],
        )

        events_by_inst: dict[UUID, list[MarketEvent]] = {}
        for event in events:
            events_by_inst.setdefault(event.instrument_id, []).append(event)

        scored: list[DigestItem] = []
        ignored: list[IgnoredItem] = []
        shown_instruments: set[UUID] = set()
        max_age: float | None = None

        for event in events:
            evidence = event.evidence.bundle if event.evidence else {}
            # Defensive: clamp absurd z on read (stale bundles before flag_modified fix)
            market = evidence.get("market_evidence")
            if isinstance(market, dict) and market.get("price_anomaly_score") is not None:
                try:
                    z_val = float(market["price_anomaly_score"])
                    if z_val > settings.max_price_anomaly_z:
                        market = {
                            **market,
                            "price_anomaly_score": float(settings.max_price_anomaly_z),
                            "price_anomaly_z_raw": market.get("price_anomaly_z_raw", z_val),
                        }
                        evidence = {**evidence, "market_evidence": market}
                except (TypeError, ValueError):
                    pass
            ctx = evidence.get("context_evidence") or {}

            if event.severity.value == "LOW":
                ignored.append(
                    IgnoredItem(
                        instrument_id=event.instrument.instrument_id,
                        symbol=event.instrument.symbol,
                        company_name=event.instrument.company_name,
                        reason="low_significance",
                        detail="Move aligned with noise thresholds — not unusual enough.",
                    )
                )
                continue

            if not severity_meets_sensitivity(event.severity, sens):
                ignored.append(
                    IgnoredItem(
                        instrument_id=event.instrument.instrument_id,
                        symbol=event.instrument.symbol,
                        company_name=event.instrument.company_name,
                        reason="below_sensitivity",
                        detail=f"Severity {event.severity.value} filtered by your {sens} sensitivity.",
                    )
                )
                continue

            # Market-aligned suppress explanation even if severity somehow higher
            mr = abs(float(ctx.get("market_residual") or 0))
            sr = abs(float(ctx.get("sector_residual") or 0))
            if (
                event.severity.value in {"LOW", "NOTABLE"}
                and mr < settings.context_threshold
                and sr < settings.context_threshold
                and not (evidence.get("information_evidence") or {}).get("filing_present")
            ):
                # Still allow NOTABLE through scoring below; Reliance-style LOW already caught
                pass

            snap = snap_by_inst.get(event.instrument_id)
            seen_states = snap.last_seen_event_states if snap else {}

            price_row = await self.session.scalar(
                select(PricePoint)
                .where(PricePoint.instrument_id == event.instrument_id)
                .order_by(PricePoint.timestamp.desc())
                .limit(1)
            )
            received = price_row.received_at if price_row else event.detected_at
            conflict_sym = (settings.demo_conflict_symbol or "").strip().upper()
            force_conflict = bool(
                conflict_sym and event.instrument.symbol.upper() == conflict_sym
            )
            conf, conf_meta = confidence_score(
                received_at=received,
                prices=[price_row.price] if price_row else [Decimal("1")],
                volume=price_row.volume if price_row else Decimal("0"),
                force_conflict=force_conflict,
            )
            age_s = (datetime.now(timezone.utc) - received).total_seconds()
            if max_age is None or age_s > max_age:
                max_age = age_s

            sig = significance_continuous(event.severity, evidence)
            nov = novelty_score(event, seen_states)
            att = attention_score(
                event,
                last_seen_event_states=seen_states,
                confidence=conf,
                evidence=evidence,
            )

            if nov <= 0:
                ignored.append(
                    IgnoredItem(
                        instrument_id=event.instrument.instrument_id,
                        symbol=event.instrument.symbol,
                        company_name=event.instrument.company_name,
                        reason="already_seen",
                        detail="You already marked this event state as seen.",
                    )
                )
                continue
            if att <= 0:
                ignored.append(
                    IgnoredItem(
                        instrument_id=event.instrument.instrument_id,
                        symbol=event.instrument.symbol,
                        company_name=event.instrument.company_name,
                        reason="zero_attention",
                        detail="Attention collapsed after confidence/novelty gates.",
                    )
                )
                continue

            # Market-aligned / beta move → ignore (incl. RVOL-only spikes: edge B4)
            filing = bool((evidence.get("information_evidence") or {}).get("filing_present"))
            z_score = float((evidence.get("market_evidence") or {}).get("price_anomaly_score") or 0)
            rvol = float((evidence.get("market_evidence") or {}).get("rvol_score") or 0)
            if (
                not filing
                and mr < settings.context_threshold
                and sr < settings.context_threshold
                and z_score < settings.notable_price_z
            ):
                detail = (
                    f"Market residual {mr:.4f} / sector residual {sr:.4f} "
                    f"below context threshold {settings.context_threshold}."
                )
                if rvol >= settings.rvol_threshold:
                    detail += f" Volume {rvol:.1f}× without idiosyncratic residual — not attention."
                ignored.append(
                    IgnoredItem(
                        instrument_id=event.instrument.instrument_id,
                        symbol=event.instrument.symbol,
                        company_name=event.instrument.company_name,
                        reason="market_aligned",
                        detail=detail,
                    )
                )
                continue

            user_note = note_by_inst.get(event.instrument_id)
            # Only LLM-narrate High cards — keeps digest under a few seconds for login UX
            if event.severity == Severity.HIGH and settings.enable_llm:
                try:
                    explained = await explain_with_optional_llm(
                        event.instrument.symbol, evidence, user_note=user_note
                    )
                except Exception:  # noqa: BLE001
                    explained = ExplanationResult(
                        text=explanation_from_evidence(event.instrument.symbol, evidence),
                        retrieval=[],
                    )
            else:
                chunks = await retrieve_for_symbol(event.instrument.symbol, evidence)
                text = explanation_from_evidence(event.instrument.symbol, evidence)
                if user_note:
                    text = f"{text} You added this name noting: “{user_note[:160]}.”"
                explained = ExplanationResult(
                    text=text,
                    retrieval=[
                        {
                            "source": c.source,
                            "title": c.title,
                            "origin": c.origin,
                            "score": round(c.score, 3),
                        }
                        for c in chunks
                    ],
                )
            peers = list(evidence.get("peers") or [])
            shown_instruments.add(event.instrument_id)
            scored.append(
                DigestItem(
                    event_id=event.event_id,
                    instrument=DigestInstrument(
                        instrument_id=event.instrument.instrument_id,
                        symbol=event.instrument.symbol,
                        company_name=event.instrument.company_name,
                    ),
                    severity=event.severity.value,
                    status=event.status.value,
                    tier=ui_tier(event, att),
                    attention_score=round(att, 4),
                    significance=round(sig, 4),
                    novelty=round(nov, 4),
                    confidence=round(conf, 4),
                    confidence_breakdown=str(conf_meta.get("breakdown") or "") or None,
                    explanation=explained.text,
                    evidence=evidence,
                    peers=peers,
                    retrieval=[RetrievalChip(**r) for r in explained.retrieval],
                    user_note=user_note,
                    user_feedback=(
                        fb_map[event.event_id].value if event.event_id in fb_map else None
                    ),
                    version=event.version,
                    detected_at=event.detected_at,
                    data_conflict=bool(conf_meta.get("data_conflict")),
                    data_age_seconds=round(age_s, 1),
                )
            )

        # Instruments on watchlist with no open event
        for item in watchlist.items:
            if item.instrument_id in shown_instruments:
                continue
            if any(i.instrument_id == item.instrument_id for i in ignored):
                continue
            if item.instrument.is_index:
                ignored.append(
                    IgnoredItem(
                        instrument_id=item.instrument_id,
                        symbol=item.instrument.symbol,
                        company_name=item.instrument.company_name,
                        reason="index_context_only",
                        detail="Indices are used for market/sector context — not scored as equities.",
                    )
                )
                continue
            if item.instrument_id not in events_by_inst:
                # Distinguish quiet vs insufficient history (edge C1)
                n_pts = await self.session.scalar(
                    select(func.count())
                    .select_from(PricePoint)
                    .where(PricePoint.instrument_id == item.instrument_id)
                )
                if (n_pts or 0) < 2:
                    ignored.append(
                        IgnoredItem(
                            instrument_id=item.instrument_id,
                            symbol=item.instrument.symbol,
                            company_name=item.instrument.company_name,
                            reason="insufficient_history",
                            detail="Fewer than 2 price points — detectors need more history.",
                        )
                    )
                else:
                    ignored.append(
                        IgnoredItem(
                            instrument_id=item.instrument_id,
                            symbol=item.instrument.symbol,
                            company_name=item.instrument.company_name,
                            reason="no_event",
                            detail="No open MarketEvent — quiet relative to detectors.",
                        )
                    )

        # Dedupe ignored by instrument (keep first reason)
        seen_ign: set[UUID] = set()
        deduped: list[IgnoredItem] = []
        for row in ignored:
            if row.instrument_id in seen_ign or row.instrument_id in shown_instruments:
                continue
            seen_ign.add(row.instrument_id)
            deduped.append(row)

        scored.sort(key=lambda i: i.attention_score, reverse=True)
        # Prefer HIGH cards in the top-K window (edge B5)
        highs = [i for i in scored if i.tier == "HIGH_ATTENTION"]
        rest = [i for i in scored if i.tier != "HIGH_ATTENTION"]
        ordered = highs + rest
        items = ordered[:top_k]
        hidden_high = max(0, len(highs) - sum(1 for i in items if i.tier == "HIGH_ATTENTION"))

        empty_hint = None
        if not items:
            if not instrument_ids:
                empty_hint = "Add instruments or describe a watchlist to start scoring."
            elif deduped:
                reasons = {}
                for row in deduped:
                    reasons[row.reason] = reasons.get(row.reason, 0) + 1
                bits = ", ".join(f"{c}× {r}" for r, c in sorted(reasons.items(), key=lambda x: -x[1])[:4])
                empty_hint = f"Caught up — filtered: {bits}."
            else:
                empty_hint = "No novel attention items right now."

        summary = DigestSummary(
            high_attention=sum(1 for i in items if i.tier == "HIGH_ATTENTION"),
            worth_watching=sum(1 for i in items if i.tier == "WORTH_WATCHING"),
            notable=sum(1 for i in items if i.tier == "NOTABLE"),
            hidden_high=hidden_high,
            ignored_count=len(deduped),
            empty_hint=empty_hint,
            headline=_digest_headline(
                items,
                ignored_count=len(deduped),
                high=sum(1 for i in items if i.tier == "HIGH_ATTENTION"),
                watch=sum(1 for i in items if i.tier == "WORTH_WATCHING"),
                notable=sum(1 for i in items if i.tier == "NOTABLE"),
            ),
        )
        # Effective mode: config says replay, but engine also ingests live-sim ticks
        latest_src = await self.session.scalar(
            select(PricePoint.source)
            .where(PricePoint.instrument_id.in_(instrument_ids))
            .order_by(PricePoint.received_at.desc())
            .limit(1)
        )
        mode = settings.market_data_mode
        if latest_src == "yahoo":
            mode = "yahoo"
        elif latest_src == "live-sim":
            mode = "replay+live-sim"

        return DigestResponse(
            generated_at=datetime.now(timezone.utc),
            last_checked_at=last_checked,
            watchlist_id=watchlist_id,
            items=items,
            ignored=deduped,
            summary=summary,
            market_data_mode=mode,
            data_age_seconds=round(max_age, 1) if max_age is not None else None,
            novelty_scope="user_instrument",
        )

    async def touch_checked(self, user_id: UUID, watchlist_id: UUID) -> dict:
        """Record Attention engagement — throttle so glancing doesn't wipe 'since last check' (A4)."""
        from datetime import timedelta

        watchlist = await self.watchlists.get_owned(watchlist_id, user_id)
        if watchlist is None:
            raise AppError("WATCHLIST_NOT_FOUND", "Watchlist not found", 404)

        instrument_ids = [item.instrument_id for item in watchlist.items]
        now = datetime.now(timezone.utc)
        min_gap = timedelta(minutes=15)
        existing = {
            s.instrument_id: s
            for s in await self.session.scalars(
                select(WatchlistSnapshot).where(
                    WatchlistSnapshot.user_id == user_id,
                    WatchlistSnapshot.instrument_id.in_(instrument_ids),
                )
            )
        }
        updated = False
        for iid in instrument_ids:
            snap = existing.get(iid)
            if snap is None:
                self.session.add(
                    WatchlistSnapshot(
                        user_id=user_id,
                        instrument_id=iid,
                        last_checked_at=now,
                        last_seen_price=None,
                        last_seen_event_states={},
                        version=1,
                    )
                )
                updated = True
            else:
                prev = snap.last_checked_at
                if prev is None or (now - prev) >= min_gap:
                    snap.last_checked_at = now
                    updated = True
        if updated:
            await self.session.commit()
        display = now
        if existing:
            display = max(
                (s.last_checked_at for s in existing.values() if s.last_checked_at),
                default=now,
            )
            if updated:
                display = now
        return {"ok": True, "last_checked_at": display.isoformat(), "updated": updated}

    async def mark_seen(
        self, user_id: UUID, watchlist_id: UUID, payload: MarkSeenRequest
    ) -> dict:
        watchlist = await self.watchlists.get_owned(watchlist_id, user_id)
        if watchlist is None:
            raise AppError("WATCHLIST_NOT_FOUND", "Watchlist not found", 404)

        instrument_ids = {item.instrument_id for item in watchlist.items}
        now = datetime.now(timezone.utc)

        for entry in payload.items:
            event = await self.session.scalar(
                select(MarketEvent).where(MarketEvent.event_id == entry.event_id)
            )
            if event is None or event.instrument_id not in instrument_ids:
                raise AppError("EVENT_NOT_FOUND", "Event not found on this watchlist", 404)

            snap = await self.session.scalar(
                select(WatchlistSnapshot).where(
                    WatchlistSnapshot.user_id == user_id,
                    WatchlistSnapshot.instrument_id == event.instrument_id,
                )
            )
            if snap is None:
                snap = WatchlistSnapshot(
                    user_id=user_id,
                    instrument_id=event.instrument_id,
                    last_checked_at=now,
                    last_seen_price=None,
                    last_seen_event_states={},
                    version=1,
                )
                self.session.add(snap)
                await self.session.flush()

            # Mark ALL open/escalated events for this instrument so duplicate
            # cards (demo + live-sim) don't leave a twin after mark-seen.
            siblings = list(
                await self.session.scalars(
                    select(MarketEvent).where(
                        MarketEvent.instrument_id == event.instrument_id,
                        MarketEvent.status.in_([EventStatus.OPEN, EventStatus.ESCALATED]),
                    )
                )
            )
            states = dict(snap.last_seen_event_states or {})
            for sib in siblings:
                states[str(sib.event_id)] = {
                    "eventId": str(sib.event_id),
                    "severitySeen": entry.severity_seen
                    if sib.event_id == event.event_id
                    else sib.severity.value,
                    "eventVersion": entry.event_version
                    if sib.event_id == event.event_id
                    else sib.version,
                    "seenAt": now.isoformat(),
                }
            snap.last_seen_event_states = states
            flag_modified(snap, "last_seen_event_states")
            snap.last_checked_at = now
            snap.version += 1

            # Clear matching in-app alerts so Alerts tab stays in sync with Attention
            await notif_svc.mark_notifications_read_for_events(
                self.session,
                user_id,
                [sib.event_id for sib in siblings],
                commit=False,
            )

        await self.session.commit()
        return {"ok": True, "marked": len(payload.items)}

    async def reset_seen(self, user_id: UUID, watchlist_id: UUID) -> dict:
        watchlist = await self.watchlists.get_owned(watchlist_id, user_id)
        if watchlist is None:
            raise AppError("WATCHLIST_NOT_FOUND", "Watchlist not found", 404)

        instrument_ids = [item.instrument_id for item in watchlist.items]
        snapshots = list(
            await self.session.scalars(
                select(WatchlistSnapshot).where(
                    WatchlistSnapshot.user_id == user_id,
                    WatchlistSnapshot.instrument_id.in_(instrument_ids),
                )
            )
        )
        for snap in snapshots:
            snap.last_seen_event_states = {}
            flag_modified(snap, "last_seen_event_states")
            snap.version += 1

        # Clear feedback labels for events on this list so Reset doesn't show stale chips (A3)
        from app.db.models.event_feedback import EventFeedback

        event_ids = list(
            await self.session.scalars(
                select(MarketEvent.event_id).where(
                    MarketEvent.instrument_id.in_(instrument_ids),
                )
            )
        )
        if event_ids:
            rows = list(
                await self.session.scalars(
                    select(EventFeedback).where(
                        EventFeedback.user_id == user_id,
                        EventFeedback.event_id.in_(event_ids),
                    )
                )
            )
            for fb in rows:
                await self.session.delete(fb)

        await self.session.commit()
        return {"ok": True, "cleared": len(snapshots)}
