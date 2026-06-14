"""Prediksi PM2.5 hari berikutnya per stasiun menggunakan model LSTM (.keras)."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from geoalchemy2.shape import to_shape
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.aod_pm25.features.prediction.loader import load_model_from_file
from apps.aod_pm25.models import AerosolOpticalDepth
from apps.database import get_db_session
from apps.weather.models import (
    PM25DataActual,
    PM25DataPrediction,
    WeatherData,
    WeatherStation,
)

logger = logging.getLogger(__name__)

# Direktori model .keras per stasiun
_MODELS_DIR = Path(__file__).resolve().parent / "ml_models"

FEATURE_COLUMNS = [
    "temp",
    "dew",
    "humidity",
    "precip",
    "windspeed",
    "AOD",
    "ISPU PM2.5",
]
SEQUENCE_LENGTH = 30


def _find_nearest_point(lat_target, lon_target, latitudes, longitudes):
    points = np.array(list(zip(latitudes, longitudes, strict=False)))
    target = np.array([lat_target, lon_target])
    distances = np.linalg.norm(points - target, axis=1)
    return distances.argmin()


async def predict_pm25_for_all_stations():
    """Jalankan prediksi PM2.5 hari berikutnya untuk semua stasiun.

    Pemanggilan load model dan prediksi dijalankan di thread agar event loop tidak
    terblokir.
    """
    async with get_db_session() as db:
        await _run_prediction(db)


async def _run_prediction(db: AsyncSession):  # noqa: PLR0915
    end_date = datetime.now(tz=UTC).date()
    start_date = end_date - timedelta(days=SEQUENCE_LENGTH + 5)

    result = await db.execute(select(WeatherStation))
    stations = result.scalars().all()

    for station in stations:
        logger.info("Processing station: %s (ID: %s)", station.name, station.id)
        pt = to_shape(station.location)
        lon, lat = pt.x, pt.y

        result = await db.execute(
            select(AerosolOpticalDepth)
            .filter(AerosolOpticalDepth.date.between(start_date, end_date))
            .order_by(AerosolOpticalDepth.date)
        )
        aod_all = result.scalars().all()

        result = await db.execute(
            select(WeatherData).filter(
                WeatherData.date.between(start_date, end_date),
                WeatherData.station_id == station.id,
            )
        )
        weather_all = result.scalars().all()

        result = await db.execute(
            select(PM25DataActual).filter(
                PM25DataActual.date.between(start_date, end_date),
                PM25DataActual.station_id == station.id,
            )
        )
        pm25_all = result.scalars().all()

        # Indeks berdasarkan tanggal untuk pencarian cepat
        weather_by_date = {w.date: w for w in weather_all}
        pm25_by_date = {p.date: p for p in pm25_all}

        records = []
        for aod in aod_all:
            aod_date = aod.date
            latitudes = [entry["latitude"] for entry in aod.data]
            longitudes = [entry["longitude"] for entry in aod.data]
            values = [entry["aod_values"] for entry in aod.data]

            try:
                idx = _find_nearest_point(lat, lon, latitudes, longitudes)
                aod_value = values[idx]
            except Exception:
                aod_value = None

            weather = weather_by_date.get(aod_date)
            pm25 = pm25_by_date.get(aod_date)

            records.append(
                {
                    "tanggal": aod_date,
                    "ISPU PM2.5": pm25.pm25_value if pm25 else None,
                    "temp": weather.temperature if weather else None,
                    "dew": weather.dew_point if weather else None,
                    "humidity": weather.humidity if weather else None,
                    "precip": weather.precipitation if weather else None,
                    "windspeed": weather.wind_speed if weather else None,
                    "AOD": aod_value,
                }
            )

        df = pd.DataFrame(records)

        if df.empty:
            logger.info("No data for station %s. Skipping.", station.name)
            continue

        for col in FEATURE_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].interpolate(method="linear")
        df = df.ffill().bfill()
        df = df.dropna()

        if len(df) < SEQUENCE_LENGTH:
            logger.info(
                "Less than %s days of data for station %s. Skipping.",
                SEQUENCE_LENGTH,
                station.name,
            )
            continue

        scaler = MinMaxScaler()
        scaler.fit(df[FEATURE_COLUMNS].values)

        sequence_raw = df[FEATURE_COLUMNS].iloc[-SEQUENCE_LENGTH:].values
        sequence_scaled = scaler.transform(sequence_raw)
        x_manual = sequence_scaled[np.newaxis, ...]

        model_path = _MODELS_DIR / f"{station.name}.keras"
        if not model_path.exists():
            logger.warning(
                "Model not found for station %s: %s", station.name, model_path
            )
            continue

        try:
            model = await load_model_from_file(str(model_path))
        except Exception as e:
            logger.exception(
                "Failed to load model for station %s", station.name, exc_info=e
            )
            continue

        # Jalankan prediksi di thread jika model.predict bersifat blocking
        try:
            y_pred = await asyncio.to_thread(model.predict, x_manual)
            y_pred_norm = float(y_pred[0][0])
        except Exception as e:
            logger.exception(
                "Prediction failed for station %s", station.name, exc_info=e
            )
            continue
        dummy = np.zeros((1, len(FEATURE_COLUMNS)))
        dummy[0, -1] = y_pred_norm
        y_pred_real = scaler.inverse_transform(dummy)[0, -1]

        logger.info("PM2.5 prediction for %s: %.2f", station.name, y_pred_real)

        last_date = df["tanggal"].max()
        prediction_date = last_date + timedelta(days=1)

        result = await db.execute(
            select(PM25DataPrediction).filter(
                PM25DataPrediction.station_id == station.id,
                PM25DataPrediction.date == prediction_date,
            )
        )
        existing = result.scalars().first()
        if existing:
            existing.pm25_value = float(y_pred_real)
        else:
            db.add(
                PM25DataPrediction(
                    station_id=station.id,
                    date=prediction_date,
                    pm25_value=float(y_pred_real),
                )
            )
        await db.commit()
