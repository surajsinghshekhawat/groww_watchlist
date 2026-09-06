"""Market/sector context residuals — v1 coarse beta (not live OLS)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextResidual:
    market_residual: float
    sector_residual: float
    market_return: float
    sector_return: float
    stock_return: float


def context_residual_v1(
    *,
    stock_return: float,
    market_return: float,
    sector_return: float,
    beta_vs_market: float,
    beta_vs_sector: float,
) -> ContextResidual:
    market_expected = beta_vs_market * market_return
    sector_expected = beta_vs_sector * sector_return
    return ContextResidual(
        market_residual=stock_return - market_expected,
        sector_residual=stock_return - sector_expected,
        market_return=market_return,
        sector_return=sector_return,
        stock_return=stock_return,
    )
