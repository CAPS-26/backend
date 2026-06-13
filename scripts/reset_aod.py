"""Reset and re-seed AOD data from JSON — run anytime without DB reset."""

import asyncio, json, logging, sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, delete
from apps.database import get_db_session
from apps.aod.models import AerosolOpticalDepth

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("reset_aod")

AOD_JSON = Path(__file__).resolve().parent / "seed_aod_full.json"


async def main():
    if not AOD_JSON.exists():
        log.error("JSON not found: %s", AOD_JSON)
        return

    with open(AOD_JSON) as f:
        entries = json.load(f)

    async with get_db_session() as db:
        r = await db.execute(select(AerosolOpticalDepth).limit(1))
        existing = r.scalars().first()
        if not existing:
            log.error("No AOD record found. Run restore_seed.py first.")
            return
        sat_id = existing.satellite_id

        today = date.today()
        start = today - timedelta(days=len(entries) - 1)

        added = 0
        for i, entry in enumerate(entries):
            d = start + timedelta(days=i)
            if d > today:
                break

            r2 = await db.execute(
                select(AerosolOpticalDepth).where(AerosolOpticalDepth.date == d)
            )
            row = r2.scalars().first()
            if row:
                row.data = entry["data"]
            else:
                db.add(AerosolOpticalDepth(
                    satellite_id=sat_id, date=d, data=entry["data"],
                ))
            added += 1
        await db.commit()
        log.info("AOD seeded: %d dates (%s to %s)", added,
                 start.isoformat(), today.isoformat())


if __name__ == "__main__":
    asyncio.run(main())
