"""
PM2.5 Predictor
Loads a trained Random Forest / sklearn model and predicts PM2.5 from feature vectors.
"""
import joblib
import pandas as pd
import os

# The trained model lives alongside this file
_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ml_models', 'best_model.pkl')

FEATURE_COLUMNS = [
    'AOD', 'tempmax', 'tempmin', 'temp',
    'feelslikemax', 'feelslikemin', 'feelslike',
    'dew', 'humidity', 'precip', 'precipcover',
    'windgust', 'windspeed', 'winddir',
    'sealevelpressure', 'cloudcover', 'visibility',
    'solarradiation', 'solarenergy', 'uvindex',
]


def predict_model(filename: str) -> pd.DataFrame:
    """Read a CSV file, run the PM2.5 estimation model, and return a DataFrame
    with columns: aod_latitude, aod_longitude, PM2.5."""
    model = joblib.load(_MODEL_PATH)
    df = pd.read_csv(filename)
    X_pred = df[FEATURE_COLUMNS]
    df['PM2.5'] = model.predict(X_pred)
    output_df = df[['aod_latitude', 'aod_longitude', 'PM2.5']]
    print(output_df)
    return output_df
