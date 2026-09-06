"""Corporate-action price adjustment before detectors.

v1: apply known split/bonus ratios from demo filings catalog.
Prices are multiplied by cumulative adjustment factor so detectors
see a continuous adjusted series.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.core.paths import filings_catalog_path
from app.seed import INSTRUMENT_IDS


@dataclass(frozen=True)
class CorporateAction:
    instrument_id: UUID
    action: str
    ratio: float
    ex_date: date


def _catalog_path() -> Path:
    return filings_catalog_path()


def load_corporate_actions(path: Path | None = None) -> list[CorporateAction]:
    p = path or _catalog_path()
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    out: list[CorporateAction] = []
    for row in raw.get("corporate_actions") or []:
        symbol = row["symbol"]
        if symbol not in INSTRUMENT_IDS:
            continue
        out.append(
            CorporateAction(
                instrument_id=INSTRUMENT_IDS[symbol],
                action=str(row.get("action", "split")),
                ratio=float(row.get("ratio", 1.0)),
                ex_date=date.fromisoformat(str(row["ex_date"])),
            )
        )
    return out


def adjustment_factor(
    instrument_id: UUID,
    as_of: datetime,
    actions: list[CorporateAction] | None = None,
) -> Decimal:
    """Factor to multiply raw price → adjusted price (post all subsequent CAs)."""
    actions = actions if actions is not None else load_corporate_actions()
    as_of_d = as_of.date() if isinstance(as_of, datetime) else as_of
    factor = Decimal("1")
    for ca in actions:
        if ca.instrument_id != instrument_id:
            continue
        # Prices before ex_date need adjustment for later split/bonus
        if as_of_d < ca.ex_date and ca.ratio > 0:
            factor *= Decimal(str(ca.ratio))
    return factor


def adjust_price(
    instrument_id: UUID,
    price: Decimal,
    as_of: datetime,
    actions: list[CorporateAction] | None = None,
) -> Decimal:
    return (price * adjustment_factor(instrument_id, as_of, actions)).quantize(Decimal("0.0001"))
