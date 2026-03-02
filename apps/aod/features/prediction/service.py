"""
Vertical Slice: PM2.5 Prediction
LSTM-based next-day PM2.5 station forecast.
Loads per-station .keras models stored in ml_models/.
"""
import os
import numpy as np
import pandas as pd
from datetime import timedelta

from django.utils import timezone

from apps.aod.models import AerosolOpticalDepth
from apps.weather.models import WeatherData, WeatherStation, pm25DataActual, pm25DataPrediction

# Directory where .keras model files live
_MODELS_DIR = os.path.join(os.path.dirname(__file__), 'ml_models')

FEATURE_COLUMNS = ["temp", "dew", "humidity", "precip", "windspeed", "AOD", "ISPU PM2.5"]
SEQUENCE_LENGTH = 30


def _find_nearest_point(lat_target, lon_target, latitudes, longitudes):
    points = np.array(list(zip(latitudes, longitudes)))
    target = np.array([lat_target, lon_target])
    distances = np.linalg.norm(points - target, axis=1)
    return distances.argmin()


def predict_pm25_for_all_stations():
    """Predict next-day PM2.5 for every weather station using the per-station LSTM model."""
    from sklearn.preprocessing import MinMaxScaler
    from tensorflow.keras.models import load_model

    end_date = timezone.now().date()
    yesterday = end_date - timedelta(days=10)
    start_date = yesterday - timedelta(days=SEQUENCE_LENGTH)

    stations = WeatherStation.objects.all()

    for station in stations:
        print(f"Processing station: {station.name} (ID: {station.id})")
        lon, lat = station.location.x, station.location.y

        aod_all = AerosolOpticalDepth.objects.filter(
            date__range=(start_date, yesterday)
        ).order_by("date")
        weather_all = WeatherData.objects.filter(
            date__range=(start_date, yesterday), station=station
        )
        pm25_all = pm25DataActual.objects.filter(
            date__range=(start_date, yesterday), station=station
        )

        records = []
        for aod in aod_all:
            aod_date = aod.date
            latitudes = [entry['latitude'] for entry in aod.data]
            longitudes = [entry['longitude'] for entry in aod.data]
            values = [entry['aod_values'] for entry in aod.data]

            try:
                idx = _find_nearest_point(lat, lon, latitudes, longitudes)
                aod_value = values[idx]
            except Exception:
                aod_value = None

            weather = weather_all.filter(date=aod_date).first()
            pm25 = pm25_all.filter(date=aod_date).first()

            records.append({
                'tanggal': aod_date,
                'ISPU PM2.5': pm25.pm25_value if pm25 else None,
                'temp': weather.temperature if weather else None,
                'dew': weather.dew_point if weather else None,
                'humidity': weather.humidity if weather else None,
                'precip': weather.precipitation if weather else None,
                'windspeed': weather.wind_speed if weather else None,
                'AOD': aod_value,
            })

        df = pd.DataFrame(records)

        if df.empty:
            print(f"No data for station {station.name}. Skipping.")
            continue

        for col in FEATURE_COLUMNS:
            df[col] = df[col].interpolate(method='linear')
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

        pm25DataPrediction.objects.update_or_create(
            station=station,
            date=yesterday,
            defaults={'pm25_value': y_pred_real}
        )
