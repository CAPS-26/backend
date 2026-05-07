"""Muat model Random Forest dan prediksi PM2.5 dari vektor fitur."""

import logging
from pathlib import Path

import joblib
import pandas as pd

logger = logging.getLogger(__name__)

# Lokasi model yang telah dilatih
_MODEL_PATH = Path(__file__).resolve().parent / "ml_models" / "best_model.pkl"

FEATURE_COLUMNS = [
    "AOD",
    "tempmax",
    "tempmin",
    "temp",
    "feelslikemax",
    "feelslikemin",
    "feelslike",
    "dew",
    "humidity",
    "precip",
    "precipcover",
    "windgust",
    "windspeed",
    "winddir",
    "sealevelpressure",
    "cloudcover",
    "visibility",
    "solarradiation",
    "solarenergy",
    "uvindex",
]


def predict_model(filename: str) -> pd.DataFrame:
    """Baca CSV, jalankan model estimasi PM2.5, dan kembalikan DataFrame."""
    model = joblib.load(_MODEL_PATH)
    df = pd.read_csv(filename)
    x_pred = df[FEATURE_COLUMNS]
    df["PM2.5"] = model.predict(x_pred)
    output_df = df[["aod_latitude", "aod_longitude", "PM2.5"]]
    logger.debug("Prediction output rows: %s", len(output_df))
    return output_df
