from datetime import date

from pydantic import BaseModel, ConfigDict


class DateInput(BaseModel):
    # Diganti dari 'date' ke 'tanggal' untuk menghindari clash dengan type 'date'
    tanggal: date


class AodPolygonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # GeoJSON format will be handled by the router/service
    type: str = "FeatureCollection"
    features: list
