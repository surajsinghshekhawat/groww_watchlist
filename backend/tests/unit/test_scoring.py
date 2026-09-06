from app.analytics.change_point import cusum_update
from app.analytics.market_context import context_residual_v1
from app.analytics.price_anomaly import price_anomaly_score, robust_z
from app.analytics.relative_volume import rvol_score
from app.db.models import EventStatus, EventType, MarketEvent
from app.db.models.market_event import Severity
from app.scoring.evidence_fusion import fuse_evidence
from app.scoring.novelty import novelty_score
from uuid import uuid4
from datetime import datetime, timezone


def test_robust_z_extreme() -> None:
    window = [0.001 + (i % 3) * 0.0001 for i in range(40)]
    z = robust_z(window, 0.05)
    assert z is not None and abs(z) > 3


def test_robust_z_zero_mad() -> None:
    assert robust_z([0.01] * 20, 0.01) is None


def test_price_anomaly_insufficient() -> None:
    result = price_anomaly_score({"5m": ([0.01], 0.02)})
    assert result.insufficient_data is True


def test_rvol_spike() -> None:
    result = rvol_score(400.0, [100.0] * 20, bucket="11:00-11:05")
    assert result.insufficient_data is False
    assert abs(result.rvol - 4.0) < 1e-6


def test_context_divergence() -> None:
    ctx = context_residual_v1(
        stock_return=0.042,
        market_return=0.006,
        sector_return=0.011,
        beta_vs_market=1.05,
        beta_vs_sector=1.1,
    )
    assert ctx.market_residual > 0.03


def test_cusum_flags_persistent_move() -> None:
    s = 0.0
    flagged = False
    for _ in range(20):
        state = cusum_update(s, 0.01, k=0.001, h=0.05)
        s = state.score
        flagged = state.flagged
    assert flagged is True


def test_fusion_information_override() -> None:
    sev = fuse_evidence({"information_evidence": {"filing_id": "x"}})
    assert sev == Severity.HIGH


def test_fusion_market_only_notable() -> None:
    sev = fuse_evidence(
        {"market_evidence": {"price_anomaly_score": 3.0, "rvol_score": 1.0}}
    )
    assert sev == Severity.NOTABLE


def test_novelty_unseen_and_seen() -> None:
    event = MarketEvent(
        event_id=uuid4(),
        instrument_id=uuid4(),
        event_type=EventType.PRICE_ANOMALY,
        detected_at=datetime.now(timezone.utc),
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
        severity=Severity.NOTABLE,
        status=EventStatus.OPEN,
        version=1,
    )
    assert novelty_score(event, {}) == 1.0
    assert (
        novelty_score(
            event,
            {str(event.event_id): {"severitySeen": "NOTABLE", "eventVersion": 1}},
        )
        == 0.0
    )
    event.severity = Severity.HIGH
    assert (
        novelty_score(
            event,
            {str(event.event_id): {"severitySeen": "NOTABLE", "eventVersion": 1}},
        )
        == 0.9
    )
