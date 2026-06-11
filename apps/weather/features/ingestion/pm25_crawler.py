"""Ambil PM2.5 real-time dari OpenMeteo Air Quality API (free, no token).

OpenMeteo: https://open-meteo.com/en/docs/air-quality-api
Fallback: AQICN (aqicn.org) jika token diset di .env
"""

import asyncio
import logging
from datetime import UTC, datetime

import httpx
from geoalchemy2.shape import to_shape
from sqlalchemy import select

from apps.database import get_db_session
from apps.weather.models import PM25DataActual, WeatherStation
from config.settings import settings

logger = logging.getLogger(__name__)

OPENMETEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# AQICN optional fallback (free token from https://aqicn.org/data-platform/token/)
AQICN_URL = "https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"


async def _fetch_openmeteo_pm25(
    client: httpx.AsyncClient, lat: float, lon: float
) -> float | None:
    resp = await client.get(
        OPENMETEO_URL,
        params={"latitude": lat, "longitude": lon, "current": "pm2_5"},
    )
    if resp.status_code != 200:
        logger.warning("OpenMeteo HTTP %d for (%.4f, %.4f)", resp.status_code, lat, lon)
        return None
    data = resp.json()
    return data.get("current", {}).get("pm2_5")


async def _fetch_aqicn_pm25(
    client: httpx.AsyncClient, lat: float, lon: float
) -> float | None:
    token = getattr(settings, "aqicn_token", None)
    if not token:
        return None
    url = AQICN_URL.format(lat=lat, lon=lon, token=token)
    resp = await client.get(url)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("status") != "ok":
        return None
    return data.get("data", {}).get("iaqi", {}).get("pm25", {}).get("v")


async def get_ispu_pm25_now():
    """Ambil PM2.5 real-time untuk semua stasiun.

    Primary: OpenMeteo (free, no token, grid-based)
    Fallback: AQICN (butuh token gratis dari aqicn.org/data-platform/token/)
    """
    async with get_db_session() as db:
        result = await db.execute(select(WeatherStation))
        stations = result.scalars().all()
        if not stations:
            return

        today = datetime.now(tz=UTC).date()
        updated = 0

        async with httpx.AsyncClient(timeout=15.0) as client:
            for station in stations:
                pt = to_shape(station.location)
                lat, lon = pt.y, pt.x

                value = await _fetch_openmeteo_pm25(client, lat, lon)
                if value is None:
                    value = await _fetch_aqicn_pm25(client, lat, lon)
                    if value is not None:
                        logger.info("[AQICN] %s: %.1f", station.name, value)

                if value is None:
                    logger.warning("[PM2.5 No Data] %s", station.name)
                    continue

                existing = await db.execute(
                    select(PM25DataActual).where(
                        PM25DataActual.station_id == station.id,
                        PM25DataActual.date == today,
                    )
                )
                record = existing.scalars().first()
                if record:
                    record.pm25_value = float(value)
                else:
                    db.add(
                        PM25DataActual(
                            station_id=station.id,
                            date=today,
                            pm25_value=float(value),
                        )
                    )
                updated += 1
                logger.info("[PM2.5] %s: %.1f µg/m³", station.name, float(value))

        await db.commit()
        logger.info("PM2.5 crawl done: %d/%d stations", updated, len(stations))
