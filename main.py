"""Titik masuk aplikasi FastAPI."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from apps.aod.features.api.router import router as aod_router
from apps.core.cache import init_cache
from apps.core.scheduler import create_scheduler, register_jobs
from apps.weather.features.api.router import router as weather_router
from config.settings import settings

# Pengaturan logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Siklus hidup aplikasi


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache_backend = await init_cache()
    logger.info("Cache initialized with %s backend.", cache_backend)

    scheduler = create_scheduler()
    app.state.scheduler = scheduler
    if settings.scheduler_enabled:
        register_jobs(scheduler)
        scheduler.start()
        logger.info("Scheduler started.")
    else:
        logger.info("Scheduler disabled via env.")

    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")


# Pembuat aplikasi

app = FastAPI(
    title="PM2.5 & AOD Jakarta API",
    description=(
        "Air quality monitoring: AOD satellite data & weather-based PM2.5 estimation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# Middleware: Pencatatan waktu permintaan
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.method} {request.url.path} - {process_time:.4f}s")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(aod_router, prefix="/api/v1/aod", tags=["AOD"])
app.include_router(weather_router, prefix="/api/v1/weather", tags=["Weather"])


@app.get("/", include_in_schema=False)
async def root():
    return {"status": "ok", "docs": "/docs"}
