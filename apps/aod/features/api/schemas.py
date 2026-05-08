from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class DateInput(BaseModel):
    tanggal: date = Field(default_factory=lambda: datetime.now().date(), example=datetime.now().strftime("%Y-%m-%d"))


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
