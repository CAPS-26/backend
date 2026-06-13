"""Restore pre-seeded database from init_seed.sql.gz on first deploy."""

import asyncio
import gzip
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from apps.database import get_db_session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("restore")

SEED_FILE = Path(__file__).resolve().parent / "init_seed.sql.gz"


async def main():
    if not SEED_FILE.exists():
        log.info("No seed file found, skipping restore.")
        return

    async with get_db_session() as db:
        r = await db.execute(text("SELECT count(*) FROM weather_data"))
        count = r.scalar()
        if count > 0:
            log.info("Database already has %d weather records, skipping restore.", count)
            return

    log.info("Empty database detected. Restoring from %s...", SEED_FILE.name)
    async with get_db_session() as db:
        with gzip.open(SEED_FILE, "rt") as f:
            sql = f.read()
        statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
        for stmt in statements:
            try:
                await db.execute(text(stmt))
            except Exception:
                pass
        await db.commit()

    async with get_db_session() as db:
        r = await db.execute(text("SELECT count(*) FROM weather_data"))
        log.info("Restore complete. weather_data now has %d records.", r.scalar())


if __name__ == "__main__":
    asyncio.run(main())
