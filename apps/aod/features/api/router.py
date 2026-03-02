"""
AOD & PM2.5 Polygon API
Replaces: apps/aod/features/api/views.py + urls.py
"""
from datetime import date, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy.orm import Session

from apps.aod.features.api.schemas import DateInput
from apps.aod.models import AerosolOpticalDepthPolygon, PolygonDataPM25
from apps.database import get_db

router = APIRouter()


def _to_geojson_fc(rows: list, value_field: str) -> Dict[str, Any]:
    """Convert a list of polygon ORM rows to a GeoJSON FeatureCollection."""
    features = []
    for row in rows:
        shape = to_shape(row.geom)
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(shape),
                "properties": {value_field: getattr(row, value_field)},
            }
        )
    return {"type": "FeatureCollection", "features": features}


# ── AOD Polygon ────────────────────────────────────────────────────────────────

@router.get(
    "/polygon/",
    summary="Ambil Data Polygon AOD Kemarin",
    description="Mengembalikan data polygon AOD untuk kemarin.",
)
def get_aod_polygon(db: Session = Depends(get_db)):
    yesterday = date.today() - timedelta(days=1)
    rows = (
        db.query(AerosolOpticalDepthPolygon)
        .filter(AerosolOpticalDepthPolygon.date == yesterday)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Tidak ada data polygon untuk tanggal kemarin.",
        )
    return _to_geojson_fc(rows, "aod_value")


@router.post(
    "/polygon/by-date/",
    summary="Ambil Data Polygon AOD Berdasarkan Tanggal",
    description="Mengembalikan data polygon AOD berdasarkan tanggal (YYYY-MM-DD).",
)
def get_aod_polygon_by_date(body: DateInput, db: Session = Depends(get_db)):
    rows = (
        db.query(AerosolOpticalDepthPolygon)
        .filter(AerosolOpticalDepthPolygon.date == body.tanggal)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Tidak ada data polygon untuk tanggal tersebut.",
        )
    return _to_geojson_fc(rows, "aod_value")


# ── PM2.5 Polygon ──────────────────────────────────────────────────────────────

@router.get(
    "/pm25/polygon/",
    summary="Ambil Data Polygon PM2.5 Kemarin",
    description="Mengembalikan data polygon PM2.5 estimasi untuk kemarin.",
)
def get_pm25_polygon(db: Session = Depends(get_db)):
    yesterday = date.today() - timedelta(days=1)
    rows = (
        db.query(PolygonDataPM25)
        .filter(PolygonDataPM25.date == yesterday)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Tidak ada data polygon untuk tanggal kemarin.",
        )
    return _to_geojson_fc(rows, "pm25_value")


@router.post(
    "/pm25/polygon/by-date/",
    summary="Ambil Data Polygon PM2.5 Berdasarkan Tanggal",
    description="Mengembalikan data polygon PM2.5 estimasi berdasarkan tanggal (YYYY-MM-DD).",
)
def get_pm25_polygon_by_date(body: DateInput, db: Session = Depends(get_db)):
    rows = (
        db.query(PolygonDataPM25)
        .filter(PolygonDataPM25.date == body.tanggal)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Tidak ada data polygon untuk tanggal tersebut.",
        )
    return _to_geojson_fc(rows, "pm25_value")
