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

    return JobStatusOut(
        job_id=job_id,
        status=status,
        enqueue_time=job_info.enqueue_time,
        start_time=result_info.start_time if result_info else None,
        finish_time=result_info.finish_time if result_info else None,
        result=result_info.result if result_info else None,
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
