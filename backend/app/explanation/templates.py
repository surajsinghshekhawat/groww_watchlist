"""Templated grounded explanations — never invent causality."""

from __future__ import annotations

from typing import Any


def template_explanation(
    *,
    symbol: str,
    stock_change_pct: float | None,
    market_change_pct: float | None,
    sector_change_pct: float | None,
    rvol: float | None,
    filing_present: bool = False,
) -> str:
    # Build clauses then join with spaces — never ", ".join on symbol + "is up…"
    # (that produced the visible "TCS, is up 3.2%…" bug).
    if stock_change_pct is not None:
        direction = "up" if stock_change_pct >= 0 else "down"
        head = f"{symbol} is {direction} {abs(stock_change_pct):.1f}% since your last check"
    else:
        head = f"{symbol} showed a flagged move since your last check"

    clauses: list[str] = [head]

    context_bits: list[str] = []
    if market_change_pct is not None:
        context_bits.append(f"market {market_change_pct:+.1f}%")
    if sector_change_pct is not None:
        context_bits.append(f"sector {sector_change_pct:+.1f}%")
    if context_bits:
        clauses.append("versus " + " and ".join(context_bits))

    if rvol is not None and rvol > 0:
        clauses.append(f"with {rvol:.1f}× normal volume for this time of day")

    sentence = " ".join(clauses) + "."
    if filing_present:
        sentence += " A company filing was published during the move."
    return sentence


def explanation_from_evidence(symbol: str, evidence: dict[str, Any]) -> str:
    market = evidence.get("market_evidence") or {}
    context = evidence.get("context_evidence") or {}
    info = evidence.get("information_evidence") or {}
    return template_explanation(
        symbol=symbol,
        stock_change_pct=_pct(context.get("stock_return")),
        market_change_pct=_pct(context.get("market_return")),
        sector_change_pct=_pct(context.get("sector_return")),
        rvol=float(market["rvol_score"]) if market.get("rvol_score") is not None else None,
        filing_present=bool(info.get("filing_id") or info.get("filing_present")),
    )


def _pct(value: Any) -> float | None:
    if value is None:
        return None
    return float(value) * 100.0
