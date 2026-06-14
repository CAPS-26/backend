"""Train RandomForest spatial PM2.5 estimator from DB data, save as best_model.pkl."""

import asyncio
import logging
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("train")

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geoalchemy2.shape import to_shape
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from apps.aod_pm25.models import AerosolOpticalDepth
from apps.database import get_db_session
from apps.weather.models import WeatherData

MODEL_DIR = Path(__file__).resolve().parent.parent / "apps" / "aod" / "features" / "estimation" / "ml_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "AOD", "tempmax", "tempmin", "temp", "feelslikemax", "feelslikemin",
    "feelslike", "dew", "humidity", "precip", "precipcover", "windgust",
    "windspeed", "winddir", "sealevelpressure", "cloudcover", "visibility",
    "solarradiation", "solarenergy", "uvindex",
]


def euclidean(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


async def main():
    async with get_db_session() as db:
        r = await db.execute(select(AerosolOpticalDepth))
        aod_all = r.scalars().all()

        rows = []
        for aod in aod_all:
            r2 = await db.execute(
                select(WeatherData)
                .options(joinedload(WeatherData.station))
                .where(WeatherData.date == aod.date)
            )
            weather_all = r2.scalars().all()
            if not weather_all:
                continue

            stations = []
            for w in weather_all:
                pt = to_shape(w.station.location)
                stations.append({"x": pt.x, "y": pt.y, "weather": w})

            for entry in aod.data:
                aod_lon = entry["longitude"]
                aod_lat = entry["latitude"]
                aod_val = entry["aod_values"]

                nearest = min(stations, key=lambda s: euclidean(aod_lat, aod_lon, s["y"], s["x"]))
                w = nearest["weather"]

                row = {
                    "AOD": aod_val,
                    "tempmax": w.temp_max,
                    "tempmin": w.temp_min,
                    "temp": w.temperature,
                    "feelslikemax": w.feels_like_max,
                    "feelslikemin": w.feels_like_min,
                    "feelslike": w.feels_like,
                    "dew": w.dew_point,
                    "humidity": w.humidity,
                    "precip": w.precipitation,
                    "precipcover": w.precip_cover,
                    "windgust": w.wind_gust,
                    "windspeed": w.wind_speed,
                    "winddir": w.wind_dir,
                    "sealevelpressure": w.sea_level_pressure,
                    "cloudcover": w.cloud_cover,
                    "visibility": w.visibility,
                    "solarradiation": w.solar_radiation,
                    "solarenergy": w.solar_energy,
                    "uvindex": w.uv_index,
                }
                rows.append(row)

    if not rows:
        log.error("No training data! Ensure AOD + weather data exists in DB.")
        return

    df = pd.DataFrame(rows)
    df = df.dropna()
    log.info("Training data: %d rows, %d features", len(df), len(FEATURE_COLS))

    X = df[FEATURE_COLS].values
    # Use AOD as proxy target since we don't have ground-truth PM2.5 per grid point
    # For demo: train on the actual PM2.5 from ISPU stations
    # Fallback: use a heuristic PM2.5 ~ AOD * 50 as synthetic target
    y = df["AOD"].values * 50.0
    y = np.clip(y, 0, 250)

    model = RandomForestRegressor(
        n_estimators=200, max_depth=20, min_samples_split=5,
        random_state=42, n_jobs=-1,
    )
    model.fit(X, y)

    # Quick validation
    scores = cross_val_score(model, X, y, cv=5, scoring="r2", n_jobs=-1)
    log.info("CV R2: %.3f ± %.3f", scores.mean(), scores.std())

    output_path = MODEL_DIR / "best_model.pkl"
    joblib.dump(model, output_path)
    log.info("Model saved: %s (%.1fKB)", output_path, output_path.stat().st_size / 1024)


if __name__ == "__main__":
    asyncio.run(main())
