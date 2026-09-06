"""Event escalation unit tests."""

from datetime import datetime, timezone
from uuid import uuid4

from app.db.models import EventStatus, EventType, MarketEvent, Severity
from app.events.escalation import apply_escalation, should_escalate


def test_should_escalate_rank() -> None:
    assert should_escalate(Severity.NOTABLE, Severity.HIGH)
    assert not should_escalate(Severity.HIGH, Severity.NOTABLE)


def test_escalation_bumps_severity_and_version() -> None:
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
    changed = apply_escalation(
        event,
        new_severity=Severity.HIGH,
        new_evidence={"market_evidence": {"price_anomaly_score": 5.0}},
    )
    assert changed is True
    assert event.severity == Severity.HIGH
    assert event.status == EventStatus.ESCALATED
    assert event.version == 2
