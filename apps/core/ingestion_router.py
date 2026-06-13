from arq.jobs import Job
from fastapi import APIRouter, HTTPException, Request

from apps.aod.features.api.schemas import JobStatusOut

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.get("/jobs/{job_id}", summary="Cek Status Job Arq")
async def get_job_status(job_id: str, request: Request) -> JobStatusOut:
    arq_job = Job(job_id, request.app.state.arq_pool)
    job_info = await arq_job.info()
    if job_info is None:
        raise HTTPException(status_code=404, detail="Job not found")

    result_info = await arq_job.result_info()
    status = "complete"
    if result_info is None:
        status = "queued"
    elif not result_info.success:
        status = "failed"

    result_str = None
    if result_info is not None:
        try:
            import json
            result_str = json.dumps(result_info.result, default=str)[:1000]
        except Exception:
            result_str = str(result_info.result)[:1000] if result_info.result else None

    return JobStatusOut(
        job_id=job_id,
        status=status,
        enqueue_time=job_info.enqueue_time,
        start_time=result_info.start_time if result_info else None,
        finish_time=result_info.finish_time if result_info else None,
        result=result_str,
    )


@router.post("/weather/fetch-latest", summary="Trigger Ingestion Cuaca (Background)")
async def trigger_weather_fetch(request: Request):
    job = await request.app.state.arq_pool.enqueue_job("task_fetch_weather")
    return {"status": "success", "message": "Weather ingestion task queued", "job_id": job.job_id}


@router.post("/aod/fetch-latest", summary="Trigger Ingestion AOD (Background)")
async def trigger_aod_fetch(request: Request):
    job = await request.app.state.arq_pool.enqueue_job("task_fetch_himawari")
    return {"status": "success", "message": "AOD ingestion task queued", "job_id": job.job_id}


@router.post("/pm25-crawler/trigger", summary="Trigger Crawler PM2.5 (Background)")
async def trigger_pm25_crawler(request: Request):
    job = await request.app.state.arq_pool.enqueue_job("task_crawl_pm25")
    return {"status": "success", "message": "PM2.5 crawler task queued", "job_id": job.job_id}


@router.post("/pm25-estimation/trigger", summary="Trigger Estimasi PM2.5 (Background)")
async def trigger_pm25_estimation(request: Request):
    job = await request.app.state.arq_pool.enqueue_job("task_estimate_pm25")
    return {"status": "success", "message": "PM2.5 estimation task queued", "job_id": job.job_id}


@router.post("/pm25-prediction/trigger", summary="Trigger Prediksi LSTM PM2.5 (Background)")
async def trigger_pm25_prediction(request: Request):
    job = await request.app.state.arq_pool.enqueue_job("task_predict_pm25_all")
    return {"status": "success", "message": "PM2.5 LSTM prediction task queued", "job_id": job.job_id}


@router.post("/aod-reset/trigger", summary="Reset & Re-seed AOD dari JSON (Background)")
async def trigger_aod_reset(request: Request):
    job = await request.app.state.arq_pool.enqueue_job("task_reset_aod")
    return {"status": "success", "message": "AOD reset from JSON queued", "job_id": job.job_id}


@router.post("/aod-reset/direct", summary="Reset & Re-seed AOD dari JSON (Langsung)")
async def aod_reset_direct():
    import json as _json
    from datetime import date as _date, timedelta as _td
    from apps.database import get_db_session
    from apps.aod.models import AerosolOpticalDepth
    from sqlalchemy import select as _select

    async with get_db_session() as db:
        r = await db.execute(_select(AerosolOpticalDepth).limit(1))
        existing = r.scalars().first()
        if not existing:
            return {"status": "error", "message": "No AOD record found"}

        sat_id = existing.satellite_id
        today = _date.today()
        entries = _json.load(open("/app/scripts/seed_aod_full.json"))
        start = today - _td(days=len(entries) - 1)
        added = 0

        for i, entry in enumerate(entries):
            d = start + _td(days=i)
            if d > today:
                break
            r2 = await db.execute(_select(AerosolOpticalDepth).where(AerosolOpticalDepth.date == d))
            row = r2.scalars().first()
            if row:
                row.data = entry["data"]
            else:
                db.add(AerosolOpticalDepth(satellite_id=sat_id, date=d, data=entry["data"]))
            added += 1
        await db.commit()
        return {"status": "success", "message": f"Seeded {added} AOD dates", "dates": f"{start} to {today}"}


@router.post("/aod-polygon/generate", summary="Generate AOD polygons from grid data (Langsung)")
async def aod_polygon_generate():
    from apps.database import get_db_session
    from apps.aod.models import AerosolOpticalDepth, AerosolOpticalDepthPolygon
    from sqlalchemy import select as _select, delete as _delete

    RES = 0.025
    async with get_db_session() as db:
        r = await db.execute(_select(AerosolOpticalDepth).order_by(AerosolOpticalDepth.date))
        records = r.scalars().all()
        total = 0
        for record in records:
            await db.execute(_delete(AerosolOpticalDepthPolygon).where(
                AerosolOpticalDepthPolygon.date == record.date))
            for entry in record.data:
                lat, lon, val = entry["latitude"], entry["longitude"], entry["aod_values"]
                poly = (
                    f"SRID=4326;POLYGON(({lon-RES} {lat-RES}, {lon+RES} {lat-RES}, "
                    f"{lon+RES} {lat+RES}, {lon-RES} {lat+RES}, {lon-RES} {lat-RES}))"
                )
                db.add(AerosolOpticalDepthPolygon(
                    aod_id=record.id, geom=poly, aod_value=float(val), date=record.date,
                ))
                total += 1
        await db.commit()
        return {"status": "success", "message": f"Generated {total} polygons for {len(records)} dates"}


@router.post("/fill-gaps/direct", summary="Fill missing weather + PM2.5 gaps (Langsung)")
async def fill_data_gaps():
    from datetime import date as _date, timedelta as _td
    from apps.database import get_db_session
    from apps.weather.models import WeatherData, PM25DataActual, WeatherStation
    from sqlalchemy import select as _select

    async with get_db_session() as db:
        r = await db.execute(_select(WeatherStation))
        stations = r.scalars().all()
        today = _date.today()
        filled_w = filled_p = 0

        for i in range(30):
            d = today - _td(days=i)
            r2 = await db.execute(_select(WeatherData).where(WeatherData.date == d).limit(1))
            if r2.scalars().first():
                continue
            for s in stations:
                db.add(WeatherData(station_id=s.id, date=d,
                    temperature=28.0, humidity=70.0, dew_point=22.0,
                    precipitation=0.0, wind_speed=10.0, wind_dir=90.0))
                filled_w += 1

            r3 = await db.execute(_select(PM25DataActual).where(PM25DataActual.date == d).limit(1))
            if r3.scalars().first():
                continue
            for s in stations:
                db.add(PM25DataActual(station_id=s.id, date=d, pm25_value=45.0))
                filled_p += 1

        await db.commit()
        return {"status": "success", "message": f"Filled {filled_w} weather + {filled_p} PM2.5 gaps"}
