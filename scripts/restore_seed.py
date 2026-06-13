"""Restore pre-seeded data on first deploy: SQL dump + AOD JSON if needed."""

import asyncio
import gzip
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text, select, func
from apps.database import get_db_session
from apps.aod.models import AerosolOpticalDepth
from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("restore")

SEED_FILE = Path(__file__).resolve().parent / "init_seed.sql.gz"
AOD_JSON = Path(__file__).resolve().parent / "seed_aod_full.json"


async def restore_sql():
    if not SEED_FILE.exists():
        log.info("No seed SQL file, skipping.")
        return

    async with get_db_session() as db:
        r = await db.execute(text("SELECT count(*) FROM weather_data"))
        if r.scalar() > 0:
            log.info("DB already has data, skipping SQL restore.")
            return

    log.info("Restoring SQL dump (%.0fKB)...", SEED_FILE.stat().st_size / 1024)
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
    log.info("SQL restore done.")


async def fill_aod_gap():
    if not AOD_JSON.exists():
        return

    async with get_db_session() as db:
        r = await db.execute(select(func.count()).select_from(AerosolOpticalDepth))
        count = r.scalar()
        if count >= 10:
            log.info("AOD has %d records, no gap to fill.", count)
            return

    log.info("AOD gap detected (%d records). Seeding from JSON...", count)
    with open(AOD_JSON) as f:
        entries = json.load(f)

    async with get_db_session() as db:
        r = await db.execute(select(AerosolOpticalDepth).limit(1))
        existing = r.scalars().first()
        sat_id = existing.satellite_id if existing else 1

        today = date.today()
        start = today - timedelta(days=len(entries))
        added = 0
        for i, entry in enumerate(entries):
            d = start + timedelta(days=i)
            if d > today:
                break
            ex = await db.execute(
                select(AerosolOpticalDepth).where(AerosolOpticalDepth.date == d)
            )
            if ex.scalars().first():
                continue
            db.add(AerosolOpticalDepth(
                satellite_id=sat_id, date=d, data=entry["data"],
            ))
            added += 1
        await db.commit()
        log.info("AOD gap filled: %d new dates (%s to %s)", added,
                 (start + timedelta(days=0)).isoformat(), today.isoformat())


async def main():
    await restore_sql()
    await fill_aod_gap()


if __name__ == "__main__":
    asyncio.run(main())
