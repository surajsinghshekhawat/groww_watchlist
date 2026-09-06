"""One-shot Railway/VPS bootstrap: migrate + seed + demo replay scores.

  python -m app.bootstrap_demo
"""

from __future__ import annotations

import asyncio

from app.core.logging import configure_logging, get_logger
from app.core.paths import replay_session_path
from app.demo_pipeline import run_demo_pipeline
from app.seed import main as seed_main

configure_logging()
logger = get_logger(__name__)


def main() -> None:
    path = replay_session_path()
    if not path.is_file():
        raise SystemExit(
            f"Replay fixture missing at {path}. "
            "Rebuild the API image so backend/data is included."
        )
    logger.info("bootstrap_replay_ok", extra={"path": str(path)})

    from alembic.config import Config
    from alembic import command

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    logger.info("bootstrap_migrate_ok")

    seed_main()
    asyncio.run(run_demo_pipeline())
    logger.info("bootstrap_demo_complete")


if __name__ == "__main__":
    main()
