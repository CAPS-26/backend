"""Prediksi PM2.5 hari berikutnya per stasiun menggunakan model LSTM (.keras)."""
import os
import numpy as np
import pandas as pd
from datetime import date, timedelta

from sqlalchemy.orm import Session

from apps.aod.models import AerosolOpticalDepth
from apps.weather.models import WeatherData, WeatherStation, PM25DataActual, PM25DataPrediction
from apps.database import get_db_session

# Direktori model .keras per stasiun
_MODELS_DIR = os.path.join(os.path.dirname(__file__), "ml_models")

FEATURE_COLUMNS = ["temp", "dew", "humidity", "precip", "windspeed", "AOD", "ISPU PM2.5"]
SEQUENCE_LENGTH = 30


def _find_nearest_point(lat_target, lon_target, latitudes, longitudes):
    points = np.array(list(zip(latitudes, longitudes)))
    target = np.array([lat_target, lon_target])
    distances = np.linalg.norm(points - target, axis=1)
    return distances.argmin()


def predict_pm25_for_all_stations():
    """Jalankan prediksi PM2.5 hari berikutnya untuk semua stasiun."""
    with get_db_session() as db:
        _run_prediction(db)


def _run_prediction(db: Session):
    from sklearn.preprocessing import MinMaxScaler
    from tensorflow.keras.models import load_model
    from geoalchemy2.shape import to_shape

    end_date = date.today()
    yesterday = end_date - timedelta(days=10)
    start_date = yesterday - timedelta(days=SEQUENCE_LENGTH)

    stations = db.query(WeatherStation).all()

    for station in stations:
        print(f"Processing station: {station.name} (ID: {station.id})")
        pt = to_shape(station.location)
        lon, lat = pt.x, pt.y

        aod_all = (
            db.query(AerosolOpticalDepth)
            .filter(AerosolOpticalDepth.date.between(start_date, yesterday))
            .order_by(AerosolOpticalDepth.date)
            .all()
        )
        weather_all = (
            db.query(WeatherData)
            .filter(WeatherData.date.between(start_date, yesterday), WeatherData.station_id == station.id)
            .all()
        )
        pm25_all = (
            db.query(PM25DataActual)
            .filter(PM25DataActual.date.between(start_date, yesterday), PM25DataActual.station_id == station.id)
            .all()
        )

        # Index berdasarkan tanggal untuk pencarian cepat
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
            print(f"No data for station {station.name}. Skipping.")
            continue

        for col in FEATURE_COLUMNS:
            df[col] = df[col].interpolate(method="linear")
        df = df.dropna()

        if len(df) < SEQUENCE_LENGTH:
            print(f"Less than {SEQUENCE_LENGTH} days of data for station {station.name}. Skipping.")
            continue

        scaler = MinMaxScaler()
        scaler.fit(df[FEATURE_COLUMNS])

        sequence_raw = df[FEATURE_COLUMNS].iloc[-SEQUENCE_LENGTH:].values
        sequence_scaled = scaler.transform(sequence_raw)
        x_manual = sequence_scaled[np.newaxis, ...]

        model_path = os.path.join(_MODELS_DIR, f"{station.name}.keras")
        if not os.path.exists(model_path):
            print(f"Model not found for station {station.name}: {model_path}")
            continue

        try:
            model = load_model(model_path)
        except Exception as e:
            print(f"Failed to load model for station {station.name}: {e}")
            continue

        y_pred_norm = model.predict(x_manual)[0][0]
        dummy = np.zeros((1, len(FEATURE_COLUMNS)))
        dummy[0, -1] = y_pred_norm
        y_pred_real = scaler.inverse_transform(dummy)[0, -1]

        print(f"PM2.5 prediction for {station.name}: {y_pred_real:.2f}")

        existing = (
            db.query(PM25DataPrediction)
            .filter(PM25DataPrediction.station_id == station.id, PM25DataPrediction.date == yesterday)
            .first()
        )
        if existing:
            existing.pm25_value = float(y_pred_real)
        else:
            db.add(
                PM25DataPrediction(
                    station_id=station.id,
                    date=yesterday,
                    pm25_value=float(y_pred_real),
                )
            )
        db.commit()
