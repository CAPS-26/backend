import logging
from typing import Any

from sqlalchemy import select

from apps.aod_pm25.features.estimation.service import estimatePm25
from apps.aod_pm25.features.ingestion.himawari_ingestor import getDataHimawari
from apps.aod_pm25.features.prediction.service import predict_pm25_for_all_stations
from apps.weather.features.ingestion.pm25_crawler import get_ispu_pm25_now
from apps.weather.features.ingestion.weather_fetcher import fetch_weather_data

logger = logging.getLogger(__name__)


async def task_reset_aod(ctx: dict[str, Any]) -> None:
    logger.info("Starting AOD reset from JSON (job %s)...", ctx.get("job_id"))
    import json
    from datetime import date, timedelta
    from pathlib import Path
    from apps.database import get_db_session
    from apps.aod_pm25.models import AerosolOpticalDepth

    json_path = Path("/app/scripts/seed_aod_full.json")
    if not json_path.exists():
        logger.error("JSON not found: %s", json_path)
        return

    with open(json_path) as f:
        entries = json.load(f)

    async with get_db_session() as db:
        r = await db.execute(select(AerosolOpticalDepth).limit(1))
        existing = r.scalars().first()
        if not existing:
            logger.error("No AOD record found")
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
        logger.info("AOD reset done: %d dates (%s to %s)", added,
                     start.isoformat(), today.isoformat())


async def task_fetch_weather(ctx: dict[str, Any]) -> None:
    logger.info("Starting weather fetch task (job %s)...", ctx.get("job_id"))
    await fetch_weather_data()


async def task_fetch_himawari(ctx: dict[str, Any]) -> None:
    logger.info("Starting Himawari ingestion task (job %s)...", ctx.get("job_id"))
    await getDataHimawari()


async def task_crawl_pm25(ctx: dict[str, Any]) -> None:
    logger.info("Starting PM2.5 crawler task (job %s)...", ctx.get("job_id"))
    await get_ispu_pm25_now()


async def task_estimate_pm25(ctx: dict[str, Any]) -> None:
    logger.info("Starting PM2.5 estimation task (job %s)...", ctx.get("job_id"))
    await estimatePm25()


async def task_predict_pm25_all(ctx: dict[str, Any]) -> None:
    logger.info("Starting PM2.5 LSTM prediction for all stations (job %s)...", ctx.get("job_id"))
    await predict_pm25_for_all_stations()
