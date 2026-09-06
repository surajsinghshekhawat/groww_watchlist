"""Significance from severity — continuous within each UI band.

Severity labels stay discrete (LOW / NOTABLE / WORTH_WATCHING / HIGH) for
explainability. The numeric Significance factor varies inside each band from
how far past fusion thresholds the evidence sits — so two WORTH_WATCHING names
no longer collapse to identical Attention.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.db.models.market_event import Severity

# Flat mid-band defaults (legacy / no-evidence fallback)
SEVERITY_WEIGHTS = {
    Severity.LOW: settings.severity_weight_low,
    Severity.NOTABLE: settings.severity_weight_notable,
    Severity.WORTH_WATCHING: settings.severity_weight_worth_watching,
    Severity.HIGH: settings.severity_weight_high,
}

# Inclusive ranges — labels stay discrete; S moves continuously inside
_BAND_RANGE: dict[Severity, tuple[float, float]] = {
    Severity.LOW: (0.05, 0.22),
    Severity.NOTABLE: (0.25, 0.52),
    Severity.WORTH_WATCHING: (0.55, 0.85),
    Severity.HIGH: (0.86, 1.0),
}


def significance_from_severity(severity: Severity) -> float:
    """Flat band mid-weight — prefer significance_continuous when evidence exists."""
    return float(SEVERITY_WEIGHTS[severity])


def evidence_excess(evidence: dict[str, Any]) -> float:
    """0 = barely crossed thresholds · 1 = strongly past them (multi-signal)."""
    market = evidence.get("market_evidence") or {}
    context = evidence.get("context_evidence") or {}
    persistence = evidence.get("persistence_evidence") or {}
    information = evidence.get("information_evidence") or {}

    z = abs(float(market.get("price_anomaly_score") or 0))
    rvol = float(market.get("rvol_score") or 0)
    mr = abs(float(context.get("market_residual") or 0))
    sr = abs(float(context.get("sector_residual") or 0))
    ctx = max(mr, sr)

    z_th = settings.notable_price_z
    rvol_th = settings.rvol_threshold
    ctx_th = settings.context_threshold

    parts: list[float] = []
    if z >= z_th:
        parts.append(_clip01((z - z_th) / max(z_th * 2.5, 1e-6)))
    if rvol >= rvol_th:
        parts.append(_clip01((rvol - rvol_th) / max(rvol_th * 2.0, 1e-6)))
    if ctx >= ctx_th:
        parts.append(_clip01((ctx - ctx_th) / max(ctx_th * 3.0, 1e-6)))
    if persistence.get("cusum_flag"):
        parts.append(0.75)
    if information.get("filing_present") or information.get("filing_id"):
        parts.append(1.0)

    if not parts:
        # Below thresholds — still allow a tiny intra-band nudge from raw z
        return _clip01(z / max(z_th * 2.0, 1e-6)) * 0.35

    # Emphasize strongest active signal, blend with average (less flat than mean alone)
    avg = sum(parts) / len(parts)
    peak = max(parts)
    return _clip01(0.55 * peak + 0.45 * avg)


def significance_continuous(severity: Severity, evidence: dict[str, Any] | None) -> float:
    """Continuous Significance inside the severity band from evidence strength."""
    lo, hi = _BAND_RANGE[severity]
    if not evidence:
        # Mid-band legacy weight, clamped into range
        mid = float(SEVERITY_WEIGHTS[severity])
        return max(lo, min(hi, mid))
    t = evidence_excess(evidence)
    return round(lo + (hi - lo) * t, 6)


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))
