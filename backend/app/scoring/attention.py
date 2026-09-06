"""Attention = significance × novelty × confidence."""

from __future__ import annotations

from typing import Any

from app.db.models.market_event import MarketEvent, Severity
from app.scoring.novelty import novelty_score
from app.scoring.significance import significance_continuous, significance_from_severity


def attention_score(
    event: MarketEvent,
    *,
    last_seen_event_states: dict,
    confidence: float,
    evidence: dict[str, Any] | None = None,
) -> float:
    if evidence is not None:
        significance = significance_continuous(event.severity, evidence)
    else:
        significance = significance_from_severity(event.severity)
    novelty = novelty_score(event, last_seen_event_states)
    score = significance * novelty * max(0.0, min(1.0, confidence))
    return max(0.0, min(1.0, score))


def ui_tier(event: MarketEvent, attention: float) -> str:
    if event.severity == Severity.HIGH and attention >= 0.5:
        return "HIGH_ATTENTION"
    if event.severity == Severity.WORTH_WATCHING:
        return "WORTH_WATCHING"
    if event.severity == Severity.NOTABLE or (
        event.severity == Severity.HIGH and attention < 0.5
    ):
        return "NOTABLE"
    return "LOW"
