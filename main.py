import logging
import time
from contextlib import asynccontextmanager

from arq import create_pool
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import Layout, SearchHotKey, get_scalar_api_reference

from apps.aod_pm25.features.api.router import router as aod_router
from apps.core.arq_app import _build_redis
from apps.core.cache import init_cache
from apps.core.ingestion_router import router as ingestion_router
from apps.weather.features.api.router import router as weather_router
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache_backend = await init_cache()
    logger.info("Cache initialized with %s backend.", cache_backend)

    arq_pool = await create_pool(_build_redis())
    app.state.arq_pool = arq_pool
    logger.info("Arq pool connected.")

    yield

    await arq_pool.close()
    logger.info("Arq pool closed.")


app = FastAPI(
    title="PM2.5 & AOD Jakarta API",
    description=(
        "Air quality monitoring: AOD satellite data & weather-based PM2.5 estimation."
    ),
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info("%s %s - %.4fs", request.method, request.url.path, process_time)
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
app.include_router(ingestion_router, prefix="/api/v1")


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="PM2.5 & AOD Jakarta API",
        servers=[{"url": "https://capstone-be.raihanpk.com", "description": "Production server"}],
    )


@app.get("/", include_in_schema=False)
async def root():
    return {"status": "ok", "docs": "/docs"}
