"""Ambil data cuaca harian dari Visual Crossing API dan simpan ke tabel WeatherData."""

import logging
import os
from datetime import UTC, datetime, timedelta

import httpx
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select

from apps.database import get_db_session
from apps.weather.models import WeatherData, WeatherStation
from config.settings import settings

API_KEY = settings.api_key
BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
HTTP_OK = 200

logger = logging.getLogger(__name__)


# Helper geometri karena GeoAlchemy2 mengembalikan WKBElement, di-parse dengan shapely


def _loc_lat(location):
    return to_shape(location).y


def _loc_lon(location):
    return to_shape(location).x


def _make_weather(station_id, date_obj, day_data):
    return WeatherData(
        station_id=station_id,
        date=date_obj,
        temperature=day_data.get("temp"),
        temp_max=day_data.get("tempmax"),
        temp_min=day_data.get("tempmin"),
        feels_like=day_data.get("feelslike"),
        feels_like_max=day_data.get("feelslikemax"),
        feels_like_min=day_data.get("feelslikemin"),
        dew_point=day_data.get("dew"),
        humidity=day_data.get("humidity"),
        wind_speed=day_data.get("windspeed"),
        wind_gust=day_data.get("windgust"),
        wind_dir=day_data.get("winddir"),
        precipitation=day_data.get("precip"),
        precip_cover=day_data.get("precipcover"),
        barometric_pressure=day_data.get("pressure"),
        sea_level_pressure=day_data.get("sealevelpressure"),
        cloud_cover=day_data.get("cloudcover"),
        visibility=day_data.get("visibility"),
        uv_index=day_data.get("uvindex"),
        solar_radiation=day_data.get("solarradiation"),
        solar_energy=day_data.get("solarenergy"),
    )


async def fetch_weather_data():
    """Ambil data cuaca hari ini untuk semua stasiun."""
    async with get_db_session() as db:
        # Ambil stasiun beserta Lat/Lon langsung via PostGIS agar tidak trigger lazy load geometri
        result = await db.execute(
            select(
                WeatherStation,
                func.ST_Y(WeatherStation.location).label("lat"),
                func.ST_X(WeatherStation.location).label("lon"),
            )
        )
        rows = result.all()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for row in rows:
                # Simpan data ke variabel lokal AGAR tidak trigger lazy load setelah commit
                station_obj = row[0]
                station_id = station_obj.id
                name = station_obj.name
                lat = row.lat
                lon = row.lon

                url = (
                    f"{BASE_URL}{lat},{lon}?unitGroup=metric&key={API_KEY}&include=days"
                )
                response = await client.get(url)

                if response.status_code == HTTP_OK:
                    data = response.json()
                    days = data.get("days", [])

                    if days:
                        day_data = days[0]
                        date_str = day_data.get("datetime")
                        if date_str:
                            date_obj = (
                                datetime.strptime(date_str, "%Y-%m-%d")
                                .replace(tzinfo=UTC)
                                .date()
                            )
                            # Cek existing menggunakan ID yang sudah disimpan di variabel lokal
                            # untuk menghindari akses ke station_obj.id yang mungkin sudah expired
                            result_existing = await db.execute(
                                select(WeatherData).filter_by(
                                    station_id=station_id, date=date_obj
                                )
                            )
                            existing = result_existing.scalars().first()
                            if not existing:
                                weather = _make_weather(station_id, date_obj, day_data)
                                db.add(weather)
                                await db.commit()
                                logger.info(
                                    "[Created] %s | %s | Temp: %s",
                                    name,
                                    date_obj,
                                    day_data.get("temp"),
                                )
                            else:
                                logger.info(
                                    "[Skipped] %s | %s already exists.",
                                    name,
                                    date_obj,
                                )
                        else:
                            logger.warning("[Missing Date] %s", name)
                    else:
                        logger.warning("[No Data] %s", name)
                else:
                    logger.warning(
                        "[Fetch Failed] %s | Status Code: %s",
                        name,
                        response.status_code,
                    )


async def fetch_weather_data_range(days_back: int = 3):
    """Ambil data cuaca untuk rentang hari tertentu (backfill)."""
    results = []
    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=days_back)

    async with get_db_session() as db:
        result = await db.execute(
            select(
                WeatherStation,
                func.ST_Y(WeatherStation.location).label("lat"),
                func.ST_X(WeatherStation.location).label("lon"),
            )
        )
        rows = result.all()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for row in rows:
                station = row[0]
                lat = row.lat
                lon = row.lon
                name = station.name

                url = (
                    f"{BASE_URL}{lat},{lon}/{start_date}/{end_date}"
                    f"?unitGroup=metric&key={API_KEY}&include=days"
                )
                response = await client.get(url)

                if response.status_code == HTTP_OK:
                    data = response.json()
                    days = data.get("days", [])

                    for day_data in days:
                        date_str = day_data.get("datetime")
                        if not date_str:
                            continue
                        date_obj = (
                            datetime.strptime(date_str, "%Y-%m-%d")
                            .replace(tzinfo=UTC)
                            .date()
                        )

                        result = await db.execute(
                            select(WeatherData).filter_by(
                                station_id=station.id, date=date_obj
                            )
                        )
                        existing = result.scalars().first()
                        if not existing:
                            weather = _make_weather(station.id, date_obj, day_data)
                            db.add(weather)
                            await db.commit()
                            results.append(
                                {
                                    "station": name,
                                    "date": str(date_obj),
                                    "status": "Created",
                                }
                            )
                        else:
                            results.append(
                                {
                                    "station": name,
                                    "date": str(date_obj),
                                    "status": "Skipped",
                                }
                            )
                else:
                    results.append(
                        {
                            "station": name,
                            "error": f"Fetch failed: {response.status_code}",
                        }
                    )

    return results
