"""Time-of-day normalized relative volume."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

EPSILON = 1e-9


@dataclass(frozen=True)
class RvolResult:
    rvol: float
    insufficient_data: bool
    bucket: str


def rvol_score(
    current_volume: float,
    historical_bucket_volumes: list[float],
    *,
    bucket: str,
) -> RvolResult:
    if current_volume < 0:
        return RvolResult(rvol=0.0, insufficient_data=True, bucket=bucket)
    if len(historical_bucket_volumes) < 3:
        return RvolResult(rvol=0.0, insufficient_data=True, bucket=bucket)

    med = float(np.median(np.asarray(historical_bucket_volumes, dtype=float)))
    if med <= EPSILON:
        return RvolResult(rvol=0.0, insufficient_data=True, bucket=bucket)

    return RvolResult(
        rvol=float(current_volume / (med + EPSILON)),
        insufficient_data=False,
        bucket=bucket,
    )
