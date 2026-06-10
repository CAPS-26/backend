import logging
from typing import Any

from apps.aod.features.estimation.service import estimatePm25
from apps.aod.features.ingestion.himawari_ingestor import getDataHimawari
from apps.aod.features.prediction.service import predict_pm25_for_all_stations
from apps.weather.features.ingestion.pm25_crawler import get_ispu_pm25_now
from apps.weather.features.ingestion.weather_fetcher import fetch_weather_data

logger = logging.getLogger(__name__)


async def task_fetch_weather(ctx: dict[str, Any]) -> None:
    logger.info("Starting weather fetch task (job %s)...", ctx.get("job_id"))
    await fetch_weather_data()


async def task_fetch_himawari(ctx: dict[str, Any]) -> None:
    logger.info("Starting Himawari ingestion task (job %s)...", ctx.get("job_id"))
    await getDataHimawari()


async def task_crawl_pm25(ctx: dict[str, Any]) -> None:
    logger.info("Starting PM2.5 crawler task (job %s)...", ctx.get("job_id"))
    await get_ispu_pm25_now()


async def task_estimate_pm25(ctx: dict[str, Any]) -> None:
    logger.info("Starting PM2.5 estimation task (job %s)...", ctx.get("job_id"))
    await estimatePm25()


async def task_predict_pm25_all(ctx: dict[str, Any]) -> None:
    logger.info("Starting PM2.5 LSTM prediction for all stations (job %s)...", ctx.get("job_id"))
    await predict_pm25_for_all_stations()
