"""Tests for continuous significance, templates, confidence breakdown."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.analytics.price_anomaly import robust_z
from app.db.models import EventStatus, EventType, MarketEvent
from app.db.models.market_event import Severity
from app.explanation.templates import template_explanation
from app.scoring.attention import attention_score
from app.scoring.confidence import confidence_score
from app.scoring.significance import evidence_excess, significance_continuous
from app.services.pipeline import _baseline_return_window


def test_template_no_stray_comma() -> None:
    text = template_explanation(
        symbol="TCS",
        stock_change_pct=3.2,
        market_change_pct=0.5,
        sector_change_pct=0.8,
        rvol=1.8,
    )
    assert "TCS, is" not in text
    assert text.startswith("TCS is up 3.2%")


def test_baseline_window_differentiates_1pct_vs_4pct() -> None:
    window = _baseline_return_window("TCS", n=60)
    z1 = robust_z(window, 0.01)
    z4 = robust_z(window, 0.04)
    assert z1 is not None and z4 is not None
    assert abs(z4) > abs(z1) * 1.5
    assert abs(z4) < 12  # not the old absurd ~14+ for mid moves


def test_continuous_significance_differs_within_band() -> None:
    mild = {
        "market_evidence": {"price_anomaly_score": 2.2, "rvol_score": 1.5},
        "context_evidence": {"market_residual": 0.018, "sector_residual": 0.016},
        "persistence_evidence": {"cusum_flag": False},
        "information_evidence": {},
    }
    strong = {
        "market_evidence": {"price_anomaly_score": 5.5, "rvol_score": 4.0},
        "context_evidence": {"market_residual": 0.04, "sector_residual": 0.035},
        "persistence_evidence": {"cusum_flag": True},
        "information_evidence": {},
    }
    s_mild = significance_continuous(Severity.WORTH_WATCHING, mild)
    s_strong = significance_continuous(Severity.WORTH_WATCHING, strong)
    assert 0.55 <= s_mild <= 0.85
    assert 0.55 <= s_strong <= 0.85
    assert s_strong > s_mild + 0.05
    assert evidence_excess(strong) > evidence_excess(mild)


def test_attention_differs_when_s_differs() -> None:
    mild_ev = {
        "market_evidence": {"price_anomaly_score": 2.2, "rvol_score": 1.6},
        "context_evidence": {"market_residual": 0.017, "sector_residual": 0.016},
        "persistence_evidence": {"cusum_flag": False},
        "information_evidence": {},
    }
    strong_ev = {
        "market_evidence": {"price_anomaly_score": 6.0, "rvol_score": 3.5},
        "context_evidence": {"market_residual": 0.045, "sector_residual": 0.04},
        "persistence_evidence": {"cusum_flag": True},
        "information_evidence": {},
    }
    event = MarketEvent(
        event_id=uuid4(),
        instrument_id=uuid4(),
        event_type=EventType.PRICE_ANOMALY,
        detected_at=datetime.now(timezone.utc),
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
        severity=Severity.WORTH_WATCHING,
        status=EventStatus.OPEN,
        version=1,
    )
    a_mild = attention_score(
        event, last_seen_event_states={}, confidence=0.8, evidence=mild_ev
    )
    a_strong = attention_score(
        event, last_seen_event_states={}, confidence=0.8, evidence=strong_ev
    )
    assert a_strong > a_mild
    assert abs(a_mild - 0.56) > 0.01 or abs(a_strong - a_mild) > 0.02


def test_confidence_conflict_breakdown() -> None:
    score, meta = confidence_score(
        received_at=datetime.now(timezone.utc),
        prices=[Decimal("100")],
        volume=Decimal("1"),
        force_conflict=True,
    )
    assert meta["data_conflict"] is True
    assert score < 0.5
    assert "DATA_CONFLICT" in str(meta["breakdown"])
    assert "confidence" in str(meta["breakdown"])
