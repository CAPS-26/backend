from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class DateInput(BaseModel):
    tanggal: str = Field(description="Format: DD-MM-YYYY (Contoh: 08-05-2026)")


class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: Any


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoJSONFeature]


class JobStatusOut(BaseModel):
    job_id: str
    status: str
    enqueue_time: datetime | None = None
    start_time: datetime | None = None
    finish_time: datetime | None = None
    result: Any = None


class PredictionTriggerOut(BaseModel):
    status: str
    message: str
    job_id: str


class StationPredictionRequest(BaseModel):
    station_name: str = Field(description="Nama stasiun (contoh: bundaran_hi)")


class StationPredictionOut(BaseModel):
    station_name: str
    station_id: int
    pm25_value: float | None
    prediction_date: date
