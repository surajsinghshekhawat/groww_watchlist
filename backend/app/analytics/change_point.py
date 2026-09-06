"""CUSUM change-point — corroborating evidence ONLY, never a standalone alert."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CusumState:
    score: float
    flagged: bool


def cusum_update(prev_s: float, return_t: float, *, k: float, h: float) -> CusumState:
    s = max(0.0, prev_s + (return_t - k))
    return CusumState(score=s, flagged=s > h)
