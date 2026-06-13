"""Ambil data cuaca dari OpenMeteo (primary, free) + Visual Crossing (fallback)."""

import asyncio
import logging
from datetime import UTC, datetime

import httpx
from geoalchemy2.shape import to_shape
from sqlalchemy import select

from apps.database import get_db_session
from apps.weather.models import WeatherData, WeatherStation
from config.settings import settings

logger = logging.getLogger(__name__)

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
VISUALCROSSING_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
API_KEY = settings.api_key or ""


def _make_weather(station_id, date_obj, day_data):
    return WeatherData(
        station_id=station_id,
        date=date_obj,
        temperature=day_data.get("temperature_2m") or day_data.get("temp"),
        temp_max=day_data.get("tempmax"),
        temp_min=day_data.get("tempmin"),
        feels_like=day_data.get("apparent_temperature") or day_data.get("feelslike"),
        feels_like_max=day_data.get("feelslikemax"),
        feels_like_min=day_data.get("feelslikemin"),
        dew_point=day_data.get("dew_point_2m") or day_data.get("dew"),
        humidity=day_data.get("relative_humidity_2m") or day_data.get("humidity"),
        wind_speed=day_data.get("wind_speed_10m") or day_data.get("windspeed"),
        wind_gust=day_data.get("windgust"),
        wind_dir=day_data.get("wind_direction_10m") or day_data.get("winddir"),
        precipitation=day_data.get("precipitation") or day_data.get("precip"),
        precip_cover=day_data.get("precipcover"),
        barometric_pressure=day_data.get("surface_pressure") or day_data.get("pressure"),
        sea_level_pressure=day_data.get("sealevelpressure"),
        cloud_cover=day_data.get("cloud_cover") or day_data.get("cloudcover"),
        visibility=day_data.get("visibility"),
        uv_index=day_data.get("uvindex"),
        solar_radiation=day_data.get("solarradiation"),
        solar_energy=day_data.get("solarenergy"),
    )


async def _fetch_openmeteo(client, lat, lon):
    resp = await client.get(OPENMETEO_URL, params={
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,dew_point_2m,"
                   "apparent_temperature,precipitation,wind_speed_10m,"
                   "wind_direction_10m,surface_pressure,cloud_cover",
        "timezone": "Asia/Jakarta",
    }, timeout=10.0)
    if resp.status_code != 200:
        return None
    data = resp.json()
    current = data.get("current", {})
    if not current:
        return None
    return {
        "temperature_2m": current.get("temperature_2m"),
        "relative_humidity_2m": current.get("relative_humidity_2m"),
        "dew_point_2m": current.get("dew_point_2m"),
        "apparent_temperature": current.get("apparent_temperature"),
        "precipitation": current.get("precipitation"),
        "wind_speed_10m": current.get("wind_speed_10m"),
        "wind_direction_10m": current.get("wind_direction_10m"),
        "surface_pressure": current.get("surface_pressure"),
        "cloud_cover": current.get("cloud_cover"),
    }


async def _fetch_visualcrossing(client, lat, lon):
    if not API_KEY:
        return None
    url = f"{VISUALCROSSING_URL}{lat},{lon}?unitGroup=metric&key={API_KEY}&include=days"
    resp = await client.get(url, timeout=15.0)
    if resp.status_code != 200:
        return None
    data = resp.json()
    days = data.get("days", [])
    if not days:
        return None
    return days[0]


async def fetch_weather_data():
    async with get_db_session() as db:
        result = await db.execute(select(WeatherStation))
        stations = result.scalars().all()
        if not stations:
            return

        today = datetime.now(UTC).date()
        async with httpx.AsyncClient() as client:
            for station in stations:
                pt = to_shape(station.location)
                lat, lon = pt.y, pt.x

                # Try OpenMeteo first (free, no key)
                day_data = await _fetch_openmeteo(client, lat, lon)
                source = "OpenMeteo"

                # Fallback to Visual Crossing
                if day_data is None:
                    day_data = await _fetch_visualcrossing(client, lat, lon)
                    source = "VisualCrossing"

                if day_data is None:
                    logger.warning("[Fetch Failed] %s", station.name)
                    continue

                existing = await db.execute(
                    select(WeatherData).where(
                        WeatherData.station_id == station.id,
                        WeatherData.date == today,
                    )
                )
                record = existing.scalars().first()
                if record:
                    record.temperature = day_data.get("temperature_2m") or day_data.get("temp")
                    record.humidity = day_data.get("relative_humidity_2m") or day_data.get("humidity")
                    record.dew_point = day_data.get("dew_point_2m") or day_data.get("dew")
                    record.wind_speed = day_data.get("wind_speed_10m") or day_data.get("windspeed")
                    record.wind_dir = day_data.get("wind_direction_10m") or day_data.get("winddir")
                    record.precipitation = day_data.get("precipitation") or day_data.get("precip")
                    record.cloud_cover = day_data.get("cloud_cover") or day_data.get("cloudcover")
                else:
                    db.add(_make_weather(station.id, today, day_data))
                await db.commit()
                logger.info("[%s] %s: %.1f°C, %.0f%%", source, station.name,
                           day_data.get("temperature_2m") or day_data.get("temp") or 0,
                           day_data.get("relative_humidity_2m") or day_data.get("humidity") or 0)
                await asyncio.sleep(0.2)

        logger.info("Weather fetch complete: %d stations", len(stations))
