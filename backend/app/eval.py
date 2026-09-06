"""Golden-scenario eval — accuracy harness for the attention story.

Run: python -m app.eval
"""

from __future__ import annotations

from app.core.config import settings
from app.db.models import Severity
from app.scoring.evidence_fusion import fuse_evidence
from app.scoring.novelty import novelty_score


class _FakeEvent:
    def __init__(self, event_id: str, severity: Severity, status, version: int = 1) -> None:
        self.event_id = event_id
        from app.db.models import EventStatus

        self.severity = severity
        self.status = status if status is not None else EventStatus.OPEN
        self.version = version


def _case_hdfc_high() -> bool:
    evidence = {
        "market_evidence": {"price_anomaly_score": settings.notable_price_z + 1, "rvol_score": 4.1},
        "context_evidence": {"market_residual": 0.03, "sector_residual": 0.02},
        "persistence_evidence": {"cusum_flag": True},
        "information_evidence": {"filing_present": True, "filing_id": "NSE-HDFCBANK"},
    }
    return fuse_evidence(evidence) == Severity.HIGH


def _case_reliance_low() -> bool:
    evidence = {
        "market_evidence": {"price_anomaly_score": 1.0, "rvol_score": 1.2},
        "context_evidence": {"market_residual": 0.002, "sector_residual": 0.001},
        "persistence_evidence": {"cusum_flag": False},
        "information_evidence": {
            "filing_id": None,
            "filing_present": False,
            "corporate_action": None,
            "earnings_window": False,
        },
    }
    return fuse_evidence(evidence) == Severity.LOW


def _case_tcs_notable() -> bool:
    # Demo calibration: mild z + residuals just over context → WORTH_WATCHING
    evidence = {
        "market_evidence": {
            "price_anomaly_score": settings.notable_price_z + 0.15,
            "rvol_score": 1.8,
        },
        "context_evidence": {"market_residual": 0.018, "sector_residual": 0.016},
        "persistence_evidence": {"cusum_flag": False},
        "information_evidence": {"filing_present": False},
    }
    sev = fuse_evidence(evidence)
    return sev == Severity.WORTH_WATCHING


def _case_novelty_mark_seen() -> bool:
    from app.db.models import EventStatus

    event = _FakeEvent("e1", Severity.HIGH, EventStatus.OPEN, version=1)
    seen = {"e1": {"severitySeen": "HIGH", "eventVersion": 1}}
    return novelty_score(event, seen) == 0.0  # type: ignore[arg-type]


def _case_novelty_escalation() -> bool:
    from app.db.models import EventStatus

    event = _FakeEvent("e1", Severity.HIGH, EventStatus.ESCALATED, version=2)
    seen = {"e1": {"severitySeen": "NOTABLE", "eventVersion": 1}}
    return novelty_score(event, seen) >= 0.8  # type: ignore[arg-type]


def main() -> None:
    cases = [
        ("hdfc_filing_is_high", _case_hdfc_high),
        ("reliance_market_aligned_is_low", _case_reliance_low),
        ("tcs_mild_is_notable_or_watch", _case_tcs_notable),
        ("mark_seen_zeros_novelty", _case_novelty_mark_seen),
        ("escalation_restores_novelty", _case_novelty_escalation),
    ]
    passed = 0
    for name, fn in cases:
        ok = bool(fn())
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        passed += int(ok)
    print(f"\n{passed}/{len(cases)} passed")
    raise SystemExit(0 if passed == len(cases) else 1)


if __name__ == "__main__":
    main()
