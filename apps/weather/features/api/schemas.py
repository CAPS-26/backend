from datetime import date
from typing import Optional

from pydantic import BaseModel


class DateInput(BaseModel):
    date: date


class WeatherDataOut(BaseModel):
    station_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    temperature: Optional[float]
    precipitation: Optional[float]
    humidity: Optional[float]
    wind_dir: Optional[float]
    wind_speed: Optional[float]


class PM25ActualOut(BaseModel):
    id: int
    station_id: int
    station_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    date: Optional[date]
    pm25_value: Optional[float]


class PM25PredictionOut(BaseModel):
    id: int
    station_id: int
    date: date
    pm25_value: Optional[float]
