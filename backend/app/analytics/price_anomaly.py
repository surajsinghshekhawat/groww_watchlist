"""Pure analytics — robust MAD multi-horizon price anomaly."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

EPSILON = 1e-9
DEFAULT_HORIZONS = ("5m", "15m", "1h", "1d")


@dataclass(frozen=True)
class PriceAnomalyResult:
    robust_z: float
    strongest_horizon: str
    insufficient_data: bool
    scores_by_horizon: dict[str, float]


def robust_z(returns_window: list[float], current_return: float) -> float | None:
    if len(returns_window) < 5:
        return None
    arr = np.asarray(returns_window, dtype=float)
    med = float(np.median(arr))
    mad = float(np.median(np.abs(arr - med)))
    if mad < EPSILON:
        # Zero MAD — insufficient dispersion; do not invent a signal.
        return None
    return (current_return - med) / (1.4826 * mad + EPSILON)


def price_anomaly_score(
    horizon_returns: dict[str, tuple[list[float], float]],
) -> PriceAnomalyResult:
    """horizon_returns: {horizon: (history_window, current_return)}"""
    scores: dict[str, float] = {}
    for horizon, (window, current) in horizon_returns.items():
        z = robust_z(window, current)
        if z is not None and np.isfinite(z):
            scores[horizon] = float(z)

    if not scores:
        return PriceAnomalyResult(
            robust_z=0.0,
            strongest_horizon="",
            insufficient_data=True,
            scores_by_horizon={},
        )

    strongest = max(scores.items(), key=lambda kv: abs(kv[1]))
    return PriceAnomalyResult(
        robust_z=strongest[1],
        strongest_horizon=strongest[0],
        insufficient_data=False,
        scores_by_horizon=scores,
    )


def percentile_band(abs_z: float, p90: float, p95: float, p99: float) -> str:
    if abs_z >= p99:
        return "EXTREME"
    if abs_z >= p95:
        return "UNUSUAL"
    if abs_z >= p90:
        return "NOTABLE"
    return "NORMAL"
