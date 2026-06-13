"""Ambil data cuaca harian dari Visual Crossing API dan simpan ke tabel WeatherData."""

import asyncio
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
    """Ambil data cuaca hari ini untuk semua stasiun secara paralel dan efisien."""
    async with get_db_session() as db:
        # 1. Ambil semua stasiun sekaligus
        result = await db.execute(
            select(
                WeatherStation,
                func.ST_Y(WeatherStation.location).label("lat"),
                func.ST_X(WeatherStation.location).label("lon"),
            )
        )
        rows = result.all()
        if not rows:
            return

        # Sequential fetch with delay to avoid Visual Crossing rate limit
        async with httpx.AsyncClient(timeout=30.0) as client:
            responses = []
            for row in rows:
                url = f"{BASE_URL}{row.lat},{row.lon}?unitGroup=metric&key={API_KEY}&include=days"
                responses.append(await client.get(url))
                await asyncio.sleep(1.0)  # avoid rate limiting

        # 3. Kumpulkan data hasil fetch untuk diproses
        new_records_data = []  # List of (station_id, name, date_obj, day_data)
        dates_to_check = set()
        station_ids_to_check = set()

        for row, response in zip(rows, responses):
            station_obj = row[0]
            if isinstance(response, Exception) or response.status_code != HTTP_OK:
                logger.warning("[Fetch Failed] %s", station_obj.name)
                continue

            data = response.json()
            days = data.get("days", [])
            if not days:
                continue

            day_data = days[0]
            date_str = day_data.get("datetime")
            if date_str:
                date_obj = (
                    datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC).date()
                )
                new_records_data.append(
                    (station_obj.id, station_obj.name, date_obj, day_data)
                )
                dates_to_check.add(date_obj)
                station_ids_to_check.add(station_obj.id)

        if not new_records_data:
            return

        # 4. Bulk Check Existing (N+1 Fix)
        # Ambil semua data yang sudah ada untuk kombinasi stasiun dan tanggal tersebut
        existing_result = await db.execute(
            select(WeatherData.station_id, WeatherData.date).where(
                WeatherData.station_id.in_(list(station_ids_to_check)),
                WeatherData.date.in_(list(dates_to_check)),
            )
        )
        existing_lookup = set(existing_result.all())  # Set berisi (station_id, date)

        # 5. Filter dan Simpan (Bulk Insert)
        for s_id, s_name, d_obj, d_data in new_records_data:
            if (s_id, d_obj) not in existing_lookup:
                weather = _make_weather(s_id, d_obj, d_data)
                db.add(weather)
                logger.info("[Created] %s | %s", s_name, d_obj)
            else:
                logger.info("[Skipped] %s | %s already exists.", s_name, d_obj)

        # get_db_session akan melakukan commit otomatis saat keluar context manager


async def fetch_weather_data_range(days_back: int = 3):
    """Ambil data cuaca rentang hari tertentu secara paralel dan efisien."""
    results = []
    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=days_back)

    async with get_db_session() as db:
        # 1. Ambil semua stasiun
        result = await db.execute(
            select(
                WeatherStation,
                func.ST_Y(WeatherStation.location).label("lat"),
                func.ST_X(WeatherStation.location).label("lon"),
            )
        )
        rows = result.all()
        if not rows:
            return []

        # 2. Parallel API Fetching
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for row in rows:
                url = (
                    f"{BASE_URL}{row.lat},{row.lon}/{start_date}/{end_date}"
                    f"?unitGroup=metric&key={API_KEY}&include=days"
                )
                tasks.append(client.get(url))

            responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. Kumpulkan semua data yang di-fetch
        fetched_data = []  # List of (station_id, name, date_obj, day_data)
        all_dates = set()
        all_station_ids = set()

        for row, response in zip(rows, responses):
            station_obj = row[0]
            if isinstance(response, Exception) or response.status_code != HTTP_OK:
                results.append(
                    {"station": station_obj.name, "error": "Fetch failed or exception"}
                )
                continue

            data = response.json()
            days_data = data.get("days", [])
            for d_data in days_data:
                date_str = d_data.get("datetime")
                if date_str:
                    d_obj = (
                        datetime.strptime(date_str, "%Y-%m-%d")
                        .replace(tzinfo=UTC)
                        .date()
                    )
                    fetched_data.append((station_obj.id, station_obj.name, d_obj, d_data))
                    all_dates.add(d_obj)
                    all_station_ids.add(station_obj.id)

        if not fetched_data:
            return results

        # 4. Bulk Check Existing
        existing_result = await db.execute(
            select(WeatherData.station_id, WeatherData.date).where(
                WeatherData.station_id.in_(list(all_station_ids)),
                WeatherData.date.in_(list(all_dates)),
            )
        )
        existing_lookup = set(existing_result.all())

        # 5. Filter dan Bulk Insert
        for s_id, s_name, d_obj, d_data in fetched_data:
            if (s_id, d_obj) not in existing_lookup:
                weather = _make_weather(s_id, d_obj, d_data)
                db.add(weather)
                results.append({"station": s_name, "date": str(d_obj), "status": "Created"})
            else:
                results.append({"station": s_name, "date": str(d_obj), "status": "Skipped"})

    return results
