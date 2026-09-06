"""Filings / information evidence loader (demo catalog)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.core.paths import filings_catalog_path
from app.seed import INSTRUMENT_IDS


@dataclass(frozen=True)
class FilingRecord:
    instrument_id: UUID
    symbol: str
    filing_id: str
    title: str
    published_at: datetime
    earnings_window: bool
    corporate_action: str | None


def _path() -> Path:
    return filings_catalog_path()


def load_filings(path: Path | None = None) -> list[FilingRecord]:
    p = path or _path()
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    out: list[FilingRecord] = []
    for row in raw.get("filings") or []:
        symbol = row["symbol"]
        if symbol not in INSTRUMENT_IDS:
            continue
        out.append(
            FilingRecord(
                instrument_id=INSTRUMENT_IDS[symbol],
                symbol=symbol,
                filing_id=row["filing_id"],
                title=row.get("title", ""),
                published_at=datetime.fromisoformat(row["published_at"]).astimezone(timezone.utc),
                earnings_window=bool(row.get("earnings_window")),
                corporate_action=row.get("corporate_action"),
            )
        )
    return out


def filing_for(instrument_id: UUID, around: datetime | None = None) -> FilingRecord | None:
    """Return filing for instrument.

    Demo corpus is dated to the replay day; live-sim timestamps are \"now\".
    Prefer same-calendar-day match, then fall back to any filing for that name
    within 7 days so rescoring does not wipe the judge story.
    """
    candidates = [f for f in load_filings() if f.instrument_id == instrument_id]
    if not candidates:
        return None
    if around is None:
        return candidates[0]

    same_day = [
        f
        for f in candidates
        if abs((f.published_at - around).total_seconds()) < 86400
    ]
    if same_day:
        return same_day[0]

    near = [
        f
        for f in candidates
        if abs((f.published_at - around).total_seconds()) < 7 * 86400
    ]
    return near[0] if near else candidates[0]


def information_evidence_for(instrument_id: UUID, around: datetime | None = None) -> dict:
    f = filing_for(instrument_id, around)
    if f is None:
        return {
            "filing_id": None,
            "filing_present": False,
            "filing_title": None,
            "corporate_action": None,
            "earnings_window": False,
        }
    return {
        "filing_id": f.filing_id,
        "filing_present": True,
        "filing_title": f.title,
        "corporate_action": f.corporate_action,
        "earnings_window": f.earnings_window,
    }
