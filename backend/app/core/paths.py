"""Resolve demo data directory across local monorepo and Docker/Railway layouts."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _candidates() -> list[Path]:
    # backend/app/core/paths.py -> parents[2]=backend|/app, parents[3]=repo|/
    here = Path(__file__).resolve()
    backend_or_app = here.parents[2]
    repo_or_fs_root = here.parents[3]
    env = (os.getenv("DATA_DIR") or "").strip()
    out: list[Path] = []
    if env:
        out.append(Path(env))
    out.extend(
        [
            backend_or_app / "data",
            repo_or_fs_root / "data",
            Path("/data"),
        ]
    )
    return out


@lru_cache(maxsize=1)
def data_dir() -> Path:
    """Directory containing `replay/` and `filings/`."""
    for candidate in _candidates():
        marker = candidate / "replay" / "demo_session.json"
        if marker.is_file():
            return candidate
    # Fallback for clearer errors / first-write paths
    return _candidates()[0]


def replay_session_path() -> Path:
    return data_dir() / "replay" / "demo_session.json"


def filings_catalog_path() -> Path:
    return data_dir() / "filings" / "demo_filings.json"


def filings_docs_dir() -> Path:
    return data_dir() / "filings" / "docs"
