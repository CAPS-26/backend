"""Pipeline estimasi PM2.5.

Data grid AOD + data cuaca stasiun terdekat → grid PM2.5 → polygon PostGIS.
"""

import asyncio
import csv
import logging
import math
from pathlib import Path

from geoalchemy2.shape import to_shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.aod.features.estimation.predictor import predict_model
from apps.aod.features.estimation.raster_converter import csvToPolygon
from apps.aod.models import AerosolOpticalDepth, PM25DataEstimate, PolygonDataPM25
from apps.database import get_db_session
from apps.weather.models import WeatherData

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[5]
_TEMP_DIR = Path(__file__).parent


def _euclidean_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def _write_csv(file_path: Path, rows: list[dict]) -> None:
    with file_path.open(mode="w", newline="") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


async def estimatePm25():
    """Jalankan estimasi spasial PM2.5 untuk semua record AOD yang belum diproses."""
    _TEMP_DIR.mkdir(parents=True, exist_ok=True)

    async with get_db_session() as db:
        await _run_estimation(db)


async def _run_estimation(db: AsyncSession):
    """Logika utama estimasi PM2.5."""
    # 1. Fetch semua data AOD
    result = await db.execute(select(AerosolOpticalDepth))
    rasterdata_all = result.scalars().all()
    if not rasterdata_all:
        return

    # 2. Bulk check untuk PM2.5 estimate yang sudah ada
    aod_ids = [r.id for r in rasterdata_all]
    existing_result = await db.execute(
        select(PM25DataEstimate.aod_id).where(PM25DataEstimate.aod_id.in_(aod_ids))
    )
    existing_aod_ids = set(existing_result.scalars().all())

    for rasterdata in rasterdata_all:
        if rasterdata.id in existing_aod_ids:
            logger.info(f"[SKIP] AOD ID {rasterdata.id} already exists.")
            continue

        aod_value = rasterdata.data
        aod_date = rasterdata.date

        # Ambil semua data cuaca untuk tanggal tersebut
        result = await db.execute(
            select(WeatherData)
            .options(joinedload(WeatherData.station))
            .filter(WeatherData.date == aod_date)
        )
        all_weather = result.scalars().all()

        if not all_weather:
            logger.warning(
                "[WARNING] No weather data for %s, skipping AOD ID %s.",
                aod_date,
                rasterdata.id,
            )
            continue

        all_stations = []
        for w in all_weather:
            pt = to_shape(w.station.location)
            all_stations.append(
                {
                    "station_id": w.station.id,
                    "location_x": pt.x,
                    "location_y": pt.y,
                    "weather_data": w,
                }
            )

        merged_rows = []
        for aod in aod_value:
            aod_lon = aod["longitude"]
            aod_lat = aod["latitude"]
            aod_val = aod["aod_values"]

            # Cari stasiun terdekat dari list stations yang sudah di-fetch
            nearest = min(
                all_stations,
                key=lambda s: _euclidean_distance(
                    aod_lat, aod_lon, s["location_y"], s["location_x"]
                ),
            )
            weather_data = nearest["weather_data"]
            w_pt_x, w_pt_y = nearest["location_x"], nearest["location_y"]

            merged_rows.append(
                {
                    "datetime": aod_date,
                    "aod_longitude": aod_lon,
                    "aod_latitude": aod_lat,
                    "station_longitude": w_pt_x,
                    "station_latitude": w_pt_y,
                    "AOD": aod_val,
                    "tempmax": weather_data.temp_max,
                    "tempmin": weather_data.temp_min,
                    "temp": weather_data.temperature,
                    "feelslikemax": weather_data.feels_like_max,
                    "feelslikemin": weather_data.feels_like_min,
                    "feelslike": weather_data.feels_like,
                    "dew": weather_data.dew_point,
                    "humidity": weather_data.humidity,
                    "precip": weather_data.precipitation,
                    "precipcover": weather_data.precip_cover,
                    "windgust": weather_data.wind_gust,
                    "windspeed": weather_data.wind_speed,
                    "winddir": weather_data.wind_dir,
                    "sealevelpressure": weather_data.sea_level_pressure,
                    "cloudcover": weather_data.cloud_cover,
                    "visibility": weather_data.visibility,
                    "solarradiation": weather_data.solar_radiation,
                    "solarenergy": weather_data.solar_energy,
                    "uvindex": weather_data.uv_index,
                }
            )

        if not merged_rows:
            logger.warning(
                f"[WARNING] No merged data for AOD ID {rasterdata.id}, skipping."
            )
            continue

        file_name = _TEMP_DIR / f"aod_data_{rasterdata.id}.csv"
        await asyncio.to_thread(_write_csv, file_name, merged_rows)

        logger.info(f"AOD ID {rasterdata.id} saved to {file_name}")

        # ML Prediction
        df = await asyncio.to_thread(predict_model, str(file_name))
        data = df.to_dict(orient="records")
        jakarta_geojson = BASE_DIR / "id-jk.geojson"
        polygondata = csvToPolygon(df, str(jakarta_geojson))

        pm25data = PM25DataEstimate(
            aod_id=rasterdata.id,
            valuepm25=data,
            date=rasterdata.date,
        )
        db.add(pm25data)
        await db.flush()

        # Bulk add polygons
        polygons_to_add = []
        for _, row in polygondata.iterrows():
            geom = row.geometry
            if geom.geom_type == "MultiPolygon":
                for poly in geom.geoms:
                    polygons_to_add.append(
                        PolygonDataPM25(
                            pm25_id=pm25data.id,
                            geom=f"SRID=4326;{poly.wkt}",
                            pm25_value=row["pm25"],
                            date=pm25data.date,
                        )
                    )
            else:
                polygons_to_add.append(
                    PolygonDataPM25(
                        pm25_id=pm25data.id,
                        geom=f"SRID=4326;{geom.wkt}",
                        pm25_value=row["pm25"],
                        date=pm25data.date,
                    )
                )
        if polygons_to_add:
            db.add_all(polygons_to_add)

        await db.commit()
        logger.info(f"[SUCCESS] PM2.5 estimation for AOD ID {rasterdata.id} saved.")

        if file_name.exists():
            file_name.unlink()
