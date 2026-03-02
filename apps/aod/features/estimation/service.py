"""
PM2.5 Estimation
Orchestrates the full estimation pipeline:
AOD grid data  +  nearest-station weather data  →  PM2.5 grid  →  PostGIS polygons
"""
import os
import csv
import math

from pathlib import Path
from sqlalchemy.orm import Session, joinedload

from apps.aod.models import AerosolOpticalDepth, PM25DataEstimate, PolygonDataPM25
from apps.weather.models import WeatherData
from apps.aod.features.estimation.predictor import predict_model
from apps.aod.features.estimation.raster_converter import csvToPolygon
from apps.database import get_db_session

BASE_DIR = Path(__file__).resolve().parents[5]

# Temporary CSV output directory
_TEMP_DIR = Path(__file__).parent


def _euclidean_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def estimatePm25():
    """Run PM2.5 spatial estimation for all unprocessed AOD records."""
    os.makedirs(_TEMP_DIR, exist_ok=True)

    with get_db_session() as db:
        _run_estimation(db)


def _run_estimation(db: Session):
    from geoalchemy2.shape import to_shape

    rasterdata_all = db.query(AerosolOpticalDepth).all()

    for rasterdata in rasterdata_all:
        aod_value = rasterdata.data
        aod_date = rasterdata.date

        existing = (
            db.query(PM25DataEstimate)
            .filter(PM25DataEstimate.aod_id == rasterdata.id)
            .first()
        )
        if existing:
            print(f"[SKIP] PM2.5 estimate for AOD ID {rasterdata.id} already exists.")
            continue

        all_weather = (
            db.query(WeatherData)
            .options(joinedload(WeatherData.station))
            .filter(WeatherData.date == aod_date)
            .all()
        )
        if not all_weather:
            print(f"[WARNING] No weather data for {aod_date}, skipping AOD ID {rasterdata.id}.")
            continue

        all_stations = []
        for w in all_weather:
            pt = to_shape(w.station.location)
            all_stations.append(
                {
                    "station_id": w.station.id,
                    "location_x": pt.x,
                    "location_y": pt.y,
                }
            )

        merged_rows = []
        for aod in aod_value:
            aod_lon = aod["longitude"]
            aod_lat = aod["latitude"]
            aod_val = aod["aod_values"]

            nearest_station_id = min(
                all_stations,
                key=lambda s: _euclidean_distance(
                    aod_lat, aod_lon, s["location_y"], s["location_x"]
                ),
            )["station_id"]

            weather_data = (
                db.query(WeatherData)
                .options(joinedload(WeatherData.station))
                .filter(WeatherData.date == aod_date, WeatherData.station_id == nearest_station_id)
                .first()
            )
            if not weather_data:
                continue

            w_pt = to_shape(weather_data.station.location)
            merged_rows.append(
                {
                    "datetime": aod_date,
                    "aod_longitude": aod_lon,
                    "aod_latitude": aod_lat,
                    "station_longitude": w_pt.x,
                    "station_latitude": w_pt.y,
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
            print(f"[WARNING] No merged data for AOD ID {rasterdata.id}, skipping.")
            continue

        file_name = _TEMP_DIR / f"aod_data_{rasterdata.id}.csv"
        with open(file_name, mode="w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=merged_rows[0].keys())
            writer.writeheader()
            writer.writerows(merged_rows)

        print(f"[INFO] AOD ID {rasterdata.id} saved to {file_name}")

        df = predict_model(str(file_name))
        print(df.shape, len(rasterdata.data))

        data = df.to_dict(orient="records")
        jakarta_geojson = BASE_DIR / "id-jk.geojson"
        polygondata = csvToPolygon(df, str(jakarta_geojson))

        pm25data = PM25DataEstimate(
            aod_id=rasterdata.id,
            valuepm25=data,
            date=rasterdata.date,
        )
        db.add(pm25data)
        db.flush()  # get pm25data.id before commit

        for _, row in polygondata.iterrows():
            geom = row.geometry
            if geom.geom_type == "MultiPolygon":
                for poly in geom.geoms:
                    db.add(
                        PolygonDataPM25(
                            pm25_id=pm25data.id,
                            geom=f"SRID=4326;{poly.wkt}",
                            pm25_value=row["pm25"],
                            date=pm25data.date,
                        )
                    )
            else:
                db.add(
                    PolygonDataPM25(
                        pm25_id=pm25data.id,
                        geom=f"SRID=4326;{geom.wkt}",
                        pm25_value=row["pm25"],
                        date=pm25data.date,
                    )
                )

        db.commit()
        print(f"[SUCCESS] PM2.5 estimation for AOD ID {rasterdata.id} saved.\n")

        if file_name.exists():
            file_name.unlink()
            print(f"Temp file {file_name} deleted.")
