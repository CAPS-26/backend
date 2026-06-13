"""Seed AOD data from JSON into DB when JAXA FTP is unavailable."""

import asyncio, json, logging, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from apps.database import get_db_session
from apps.aod.models import AerosolOpticalDepth

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("seed_aod")

JSON_FILE = Path(__file__).resolve().parent / "seed_aod_full.json"


async def main():
    if not JSON_FILE.exists():
        log.error("JSON file not found: %s", JSON_FILE)
        return

    with open(JSON_FILE) as f:
        entries = json.load(f)

    async with get_db_session() as db:
        r = await db.execute(select(AerosolOpticalDepth).limit(1))
        existing = r.scalars().first()
        sat_id = existing.satellite_id if existing else 1

        # Map JSON entries (30 items) to last 30 calendar days
        from datetime import date as dt, timedelta
        today = dt.today()
        start = today - timedelta(days=30)

        count = 0
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
                satellite_id=sat_id,
                date=d,
                data=entry["data"],
            ))
            count += 1
        await db.commit()
        log.info("Seeded %d AOD dates (from %s to %s)", count,
                 (start + timedelta(days=0)).isoformat(),
                 today.isoformat())


if __name__ == "__main__":
    asyncio.run(main())
