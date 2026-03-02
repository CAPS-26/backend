"""
Weather & PM2.5 Station API
Replaces: apps/weather/features/api/views.py + urls.py
"""
from datetime import date as date_type
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session, joinedload

from apps.database import get_db
from apps.weather.features.api.schemas import DateInput
from apps.weather.models import PM25DataActual, PM25DataPrediction, WeatherData

router = APIRouter()


def _coords(station) -> tuple:
    """Return (lat, lon) from a WeatherStation GeoAlchemy2 Point, or (None, None)."""
    if station and station.location:
        pt = to_shape(station.location)
        return pt.y, pt.x
    return None, None


def _weather_row(r: WeatherData) -> Dict[str, Any]:
    lat, lon = _coords(r.station)
    return {
        "station_name": r.station.name if r.station else None,
        "latitude": lat,
        "longitude": lon,
        "temperature": r.temperature,
        "precipitation": r.precipitation,
        "humidity": r.humidity,
        "wind_dir": r.wind_dir,
        "wind_speed": r.wind_speed,
    }


def _pm25_actual_row(r: PM25DataActual) -> Dict[str, Any]:
    lat, lon = _coords(r.station)
    return {
        "id": r.id,
        "station_id": r.station_id,
        "station_name": r.station.name if r.station else None,
        "latitude": lat,
        "longitude": lon,
        "date": r.date,
        "pm25_value": r.pm25_value,
    }


# ── Weather ────────────────────────────────────────────────────────────────────

@router.get(
    "/weather/",
    summary="Ambil Data Cuaca Hari Ini",
    description="Mengembalikan data cuaca dari seluruh stasiun untuk hari ini.",
)
def get_latest_weather(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    today = date_type.today()
    rows = (
        db.query(WeatherData)
        .options(joinedload(WeatherData.station))
        .filter(WeatherData.date == today)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Tidak ada data cuaca untuk tanggal {today}.",
        )
    return [_weather_row(r) for r in rows]


@router.post(
    "/weather/by-date/",
    summary="Ambil Data Cuaca Berdasarkan Tanggal",
    description="Mengembalikan data cuaca berdasarkan tanggal (YYYY-MM-DD).",
)
def get_weather_by_date(body: DateInput, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    rows = (
        db.query(WeatherData)
        .options(joinedload(WeatherData.station))
        .filter(WeatherData.date == body.date)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Tidak ada data cuaca untuk tanggal {body.date}.",
        )
    return [_weather_row(r) for r in rows]


# ── PM2.5 Actual ───────────────────────────────────────────────────────────────

@router.get(
    "/pm25/actual/",
    summary="Ambil Data PM2.5 Aktual Hari Ini",
)
def get_latest_pm25_actual(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    today = date_type.today()
    rows = (
        db.query(PM25DataActual)
        .options(joinedload(PM25DataActual.station))
        .filter(PM25DataActual.date == today)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Tidak ada data PM2.5 untuk tanggal {today}.",
        )
    return [_pm25_actual_row(r) for r in rows]


@router.post(
    "/pm25/actual/by-date/",
    summary="Ambil Data PM2.5 Aktual Berdasarkan Tanggal",
)
def get_pm25_actual_by_date(body: DateInput, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    rows = (
        db.query(PM25DataActual)
        .options(joinedload(PM25DataActual.station))
        .filter(PM25DataActual.date == body.date)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Tidak ada data PM2.5 untuk tanggal {body.date}.",
        )
    return [_pm25_actual_row(r) for r in rows]


# ── PM2.5 Prediction ───────────────────────────────────────────────────────────

@router.get(
    "/pm25/prediction/",
    summary="Ambil Data PM2.5 Prediksi Hari Ini",
)
def get_latest_pm25_prediction(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    today = date_type.today()
    rows = (
        db.query(PM25DataPrediction)
        .filter(PM25DataPrediction.date == today)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Tidak ada data PM2.5 prediksi untuk tanggal {today}.",
        )
    return [
        {"id": r.id, "station_id": r.station_id, "date": r.date, "pm25_value": r.pm25_value}
        for r in rows
    ]


@router.post(
    "/pm25/prediction/by-date/",
    summary="Ambil Data PM2.5 Prediksi Berdasarkan Tanggal",
)
def get_pm25_prediction_by_date(body: DateInput, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    rows = (
        db.query(PM25DataPrediction)
        .filter(PM25DataPrediction.date == body.date)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Tidak ada data PM2.5 prediksi untuk tanggal {body.date}.",
        )
    return [
        {"id": r.id, "station_id": r.station_id, "date": r.date, "pm25_value": r.pm25_value}
        for r in rows
    ]
