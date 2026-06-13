"""Muat model ExtraTrees spatial PM2.5 dan prediksi dari vektor fitur."""

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_MODEL_DIR = Path(__file__).resolve().parent / "ml_models"
_MODEL_PATH = _MODEL_DIR / "spatial_pm25_etr.pkl"

FEATURE_COLUMNS = [
    "latitude", "longitude",
    "temperature_2m", "apparent_temperature", "relative_humidity_2m",
    "dew_point_2m", "precipitation", "rain", "surface_pressure",
    "cloud_cover_total", "u_wind", "v_wind", "jam", "bulan",
    "hari_dalam_minggu", "is_weekend", "AOD",
    "v_wind_lag1", "u_wind_lag1", "temp_lag1", "rh_lag1",
]


def predict_model(filename: str) -> pd.DataFrame:
    """Baca CSV, jalankan model estimasi PM2.5, dan kembalikan DataFrame."""
    model = joblib.load(_MODEL_PATH)
    df = pd.read_csv(filename)
    df["PM2.5"] = np.clip(model.predict(df[FEATURE_COLUMNS].values), 0, 500)
    output_df = df[["aod_latitude", "aod_longitude", "PM2.5"]]
    logger.debug("Prediction output rows: %s", len(output_df))
    return output_df
