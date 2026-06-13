"""Restore pre-seeded database from init_seed.sql.gz on first deploy."""

import asyncio
import gzip
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from apps.database import get_db_session
from config.settings import settings

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

    log.info("Empty database detected. Restoring from %s (%.0fKB)...",
             SEED_FILE.name, SEED_FILE.stat().st_size / 1024)

    # Use asyncpg directly to handle pg_dump COPY statements properly
    import asyncpg
    conn = await asyncpg.connect(
        host=settings.dbhost, port=int(settings.dbport),
        user=settings.userdb, password=settings.passdb,
        database=settings.namedb,
    )
    try:
        with gzip.open(SEED_FILE, "rt") as f:
            await conn.execute(f.read())
    finally:
        await conn.close()

    async with get_db_session() as db:
        r = await db.execute(text("SELECT count(*) FROM weather_data"))
        log.info("Restore complete. weather_data: %d records.", r.scalar())


if __name__ == "__main__":
    asyncio.run(main())
