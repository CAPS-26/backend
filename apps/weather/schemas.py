from datetime import date

from pydantic import BaseModel, ConfigDict


class DateInput(BaseModel):
    # Rename to avoid clash with 'date' type annotation in Pydantic v2
    target_date: date


class WeatherDataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    station_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    temperature: float | None = None
    precipitation: float | None = None
    humidity: float | None = None
    wind_dir: float | None = None
    wind_speed: float | None = None


class PM25ActualOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_id: int
    station_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    date: date | None = None
    pm25_value: float | None = None


class PM25PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_id: int
    date: date
    pm25_value: float | None = None
