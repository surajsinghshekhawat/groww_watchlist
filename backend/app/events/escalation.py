"""Event escalation — same event, new evidence / higher severity → version++."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from app.db.models import EventStatus, MarketEvent, Severity

_SEVERITY_RANK = {
    Severity.LOW: 0,
    Severity.NOTABLE: 1,
    Severity.WORTH_WATCHING: 2,
    Severity.HIGH: 3,
}


def should_escalate(current: Severity, incoming: Severity) -> bool:
    return _SEVERITY_RANK[incoming] > _SEVERITY_RANK[current]


def apply_escalation(
    event: MarketEvent,
    *,
    new_severity: Severity,
    new_evidence: dict[str, Any],
) -> bool:
    """Update event in-place. Returns True if version bumped.

    Live ingest may refresh evidence numbers every few seconds — that must NOT
    bump version unless severity actually rises (otherwise mark-seen never sticks).
    """
    severity_rose = should_escalate(event.severity, new_severity)
    if severity_rose:
        event.severity = new_severity
        event.status = EventStatus.ESCALATED
    elif (
        _SEVERITY_RANK[new_severity] < _SEVERITY_RANK[event.severity]
        and event.status == EventStatus.OPEN
        and event.version == 1
    ):
        # Soft re-score down only for never-escalated open events (demo rescore)
        event.severity = new_severity

    if event.evidence is not None:
        merged = dict(event.evidence.bundle or {})
        for key, value in new_evidence.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                if key == "information_evidence":
                    old_info = merged.get(key) or {}
                    incoming = dict(value)
                    # Never erase a known filing with an empty live refresh
                    if old_info.get("filing_present") and not incoming.get("filing_present"):
                        for k in (
                            "filing_present",
                            "filing_id",
                            "filing_title",
                            "corporate_action",
                            "earnings_window",
                        ):
                            if k in old_info:
                                incoming[k] = old_info[k]
                    merged[key] = {**old_info, **incoming}
                else:
                    # Prefer incoming detector values on rescore (not stale max)
                    merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        event.evidence.bundle = merged
        flag_modified(event.evidence, "bundle")

    if severity_rose:
        event.version += 1
        return True
    return False
