from datetime import date, datetime

from pydantic import BaseModel, Field


class DateInput(BaseModel):
    date: date = Field(default_factory=lambda: datetime.now().date(), example=datetime.now().strftime("%Y-%m-%d"))


class WeatherDataOut(BaseModel):
    station_name: str | None
    latitude: float | None
    longitude: float | None
    temperature: float | None
    precipitation: float | None
    humidity: float | None
    wind_dir: float | None
    wind_speed: float | None


class PM25ActualOut(BaseModel):
    id: int
    station_id: int
    station_name: str | None
    latitude: float | None
    longitude: float | None
    date: date | None
    pm25_value: float | None


class PM25PredictionOut(BaseModel):
    id: int
    station_id: int
    date: date
    pm25_value: float | None
