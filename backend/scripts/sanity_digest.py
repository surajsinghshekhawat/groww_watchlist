"""End-to-end sanity: continuous S, conflict, explanations, no absurd z."""

from __future__ import annotations

import asyncio
import sys
from collections import Counter

# Avoid Windows cp1252 crashes on console prints
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models import MarketEvent, User
from app.db.models.market_event import Severity
from app.db.session import AsyncSessionLocal
from app.explanation.templates import explanation_from_evidence
from app.scoring.significance import significance_continuous
from app.seed import DEMO_WATCHLIST_ID
from app.services.digest_service import DigestService


async def main() -> None:
    errors: list[str] = []
    print("=== config ===")
    print(f"mode={settings.market_data_mode}")
    print(f"conflict_symbol={settings.demo_conflict_symbol!r}")
    print(f"skip_cal={settings.demo_skip_calibration}")
    print(f"max_z={settings.max_price_anomaly_z}")

    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == "demo@example.com"))
        if user is None:
            raise SystemExit("demo user missing — run seed")
        sens = user.sensitivity.value if hasattr(user.sensitivity, "value") else str(user.sensitivity)
        print(f"demo_sensitivity={sens}")
        if sens == "HIGH":
            errors.append(
                "demo user sensitivity is HIGH — Worth-watching cards (TCS conflict) are hidden; "
                "run `python -m app.seed` to reset to MEDIUM"
            )

        digest = await DigestService(session).get_digest(user.user_id, DEMO_WATCHLIST_ID)
        print("\n=== digest summary ===")
        print(f"headline={digest.summary.headline}")
        print(
            f"counts H/W/N/ign={digest.summary.high_attention}/"
            f"{digest.summary.worth_watching}/{digest.summary.notable}/"
            f"{digest.summary.ignored_count}"
        )
        print(f"items={len(digest.items)} ignored={len(digest.ignored)}")

        if not digest.summary.headline:
            errors.append("missing summary.headline")

        by_sev: dict[str, list[float]] = {}
        for item in digest.items:
            by_sev.setdefault(item.severity, []).append(item.attention_score)
            text = item.explanation or ""
            if f"{item.instrument.symbol}, is" in text:
                errors.append(f"stray comma in explanation: {text[:80]}")
            if not item.confidence_breakdown:
                errors.append(f"{item.instrument.symbol}: missing confidence_breakdown")

            z = float((item.evidence.get("market_evidence") or {}).get("price_anomaly_score") or 0)
            if z > settings.max_price_anomaly_z + 0.01:
                errors.append(f"{item.instrument.symbol}: z={z} above cap")

            sig = significance_continuous(Severity(item.severity), item.evidence)
            if abs(sig - item.significance) > 0.02:
                errors.append(
                    f"{item.instrument.symbol}: S card={item.significance} recomputed={sig}"
                )

            print(
                f"  {item.instrument.symbol:10} sev={item.severity:14} "
                f"A={item.attention_score:.3f} S={item.significance:.3f} "
                f"N={item.novelty:.2f} C={item.confidence:.2f} "
                f"conflict={item.data_conflict} z={z:.2f}"
            )
            print(f"             C: {item.confidence_breakdown}")
            print(f"             {text[:100]}")

        conflict_sym = (settings.demo_conflict_symbol or "").upper()
        if conflict_sym and sens != "HIGH":
            hit = next((i for i in digest.items if i.instrument.symbol == conflict_sym), None)
            if hit is None:
                errors.append(
                    f"{conflict_sym} not in digest — conflict beat invisible "
                    f"(ignored={[i.symbol + ':' + i.reason for i in digest.ignored]})"
                )
            else:
                if not hit.data_conflict:
                    errors.append(f"{conflict_sym} should have data_conflict=True")
                if hit.confidence >= 0.75:
                    errors.append(
                        f"{conflict_sym} confidence should be demoted, got {hit.confidence}"
                    )
                if "DATA_CONFLICT" not in (hit.confidence_breakdown or ""):
                    errors.append(f"{conflict_sym} breakdown should mention DATA_CONFLICT")

        for sev, scores in by_sev.items():
            if len(scores) >= 2 and len(set(round(s, 3) for s in scores)) == 1:
                print(f"warn: all {sev} Attention scores identical: {scores}")

        events = list(
            await session.scalars(
                select(MarketEvent)
                .options(
                    selectinload(MarketEvent.evidence),
                    selectinload(MarketEvent.instrument),
                )
                .limit(30)
            )
        )
        for ev in events:
            if not ev.evidence:
                continue
            expl = explanation_from_evidence(ev.instrument.symbol, ev.evidence.bundle or {})
            if f"{ev.instrument.symbol}, is" in expl:
                errors.append(f"event template comma: {expl}")

        reasons = Counter(i.reason for i in digest.ignored)
        print(f"\nignored reasons: {dict(reasons)}")

        # Hero story sanity
        if not any(i.instrument.symbol == "HDFCBANK" and i.tier == "HIGH_ATTENTION" for i in digest.items):
            errors.append("HDFCBANK HIGH_ATTENTION missing from Morning Watch digest")
        if not any(i.symbol == "RELIANCE" for i in digest.ignored):
            print("warn: RELIANCE not in ignored strip (check market_aligned / low)")

    print("\n=== result ===")
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        raise SystemExit(1)
    print("OK — digest sanity passed")


if __name__ == "__main__":
    asyncio.run(main())
