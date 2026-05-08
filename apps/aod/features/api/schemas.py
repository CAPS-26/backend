from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class DateInput(BaseModel):
    tanggal: date = Field(description="Format: DD-MM-YYYY (Contoh: 08-05-2026)")


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
