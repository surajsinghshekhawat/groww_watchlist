"""Event-state-aware novelty — not purely timestamp-based."""

from __future__ import annotations

from typing import Any

from app.db.models.market_event import EventStatus, MarketEvent, Severity

_SEVERITY_RANK = {
    Severity.LOW: 0,
    Severity.NOTABLE: 1,
    Severity.WORTH_WATCHING: 2,
    Severity.HIGH: 3,
}


def novelty_score(event: MarketEvent, last_seen_event_states: dict[str, Any]) -> float:
    key = str(event.event_id)
    seen = last_seen_event_states.get(key)
    if seen is None:
        return 1.0

    severity_seen = seen.get("severitySeen") or seen.get("severity_seen")
    version_seen = seen.get("eventVersion") or seen.get("event_version")

    # Same severity already acknowledged → stay hidden even if version ticks from live ingest
    if severity_seen is not None and str(event.severity.value) == str(severity_seen):
        return 0.0

    if severity_seen is not None:
        try:
            seen_sev = Severity(str(severity_seen))
            if _SEVERITY_RANK[event.severity] > _SEVERITY_RANK[seen_sev]:
                return 0.9
        except ValueError:
            if str(event.severity.value) != str(severity_seen):
                return 0.9

    if version_seen is not None and int(version_seen) != int(event.version):
        # Only resurface on version bump when severity also moved up (handled above)
        # or status explicitly escalated with unseen severity
        if event.status == EventStatus.ESCALATED and severity_seen is not None:
            try:
                if _SEVERITY_RANK[event.severity] > _SEVERITY_RANK[Severity(str(severity_seen))]:
                    return 0.85
            except ValueError:
                return 0.85
        return 0.0

    if event.status == EventStatus.ESCALATED and severity_seen is None:
        return 0.8
    return 0.0
