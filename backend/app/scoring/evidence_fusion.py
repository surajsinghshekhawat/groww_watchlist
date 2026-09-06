"""Evidence fusion — grouped corroboration, not linear summing."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.db.models.market_event import Severity


def fuse_evidence(evidence: dict[str, Any]) -> Severity:
    market = evidence.get("market_evidence") or {}
    context = evidence.get("context_evidence") or {}
    persistence = evidence.get("persistence_evidence") or {}
    information = evidence.get("information_evidence") or {}

    has_market = bool(market) and (
        float(market.get("price_anomaly_score", 0)) > settings.notable_price_z
        or float(market.get("rvol_score", 0)) > settings.rvol_threshold
    )
    has_context = bool(context) and (
        abs(float(context.get("market_residual", 0))) > settings.context_threshold
        or abs(float(context.get("sector_residual", 0))) > settings.context_threshold
    )
    has_persistence = bool(persistence) and bool(persistence.get("cusum_flag"))
    has_information = bool(information) and any(
        bool(v) for v in information.values() if v is not None
    )

    if has_information:
        return Severity.HIGH
    if has_market and has_context and has_persistence:
        return Severity.HIGH
    if has_market and has_context:
        return Severity.WORTH_WATCHING
    if has_market:
        return Severity.NOTABLE
    return Severity.LOW
