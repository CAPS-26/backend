import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select

# Tambahkan root proyek ke sys.path agar bisa mengimpor 'apps'
sys.path.append(str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)

from apps.database import get_db_session  # noqa: E402
from apps.weather.features.ingestion.pm25_crawler import (  # noqa: E402
    get_ispu_pm25_now,
)
from apps.weather.features.ingestion.weather_fetcher import (  # noqa: E402
    fetch_weather_data,
)
from apps.weather.models import WeatherStation  # noqa: E402

#   Nama Stasiun      Lokasi
#   us_embassy_1/2    US Embassy, Jl. Medan Merdeka Selatan 3-5 — Jakarta Pusat
#   jakarta_gbk       Gelora Bung Karno (Senayan) — Jakarta Selatan
#   bundaran_hi       DKI-1 Bundaran Hotel Indonesia — Jakarta Pusat
#   kelapa_gading     DKI-2 Kelapa Gading — Jakarta Utara
#   jagakarsa         DKI-3 Jagakarsa — Jakarta Selatan
#   lubang_buaya      DKI-4 Lubang Buaya — Jakarta Timur
#   kebun_jeruk       DKI-5 Kebun Jeruk — Jakarta Barat
# ---------------------------------------------------------------------------
STATIONS = [
    # nama               lon         lat
    ("us_embassy_1", 106.8279877, -6.1811056),
    ("us_embassy_2", 106.79319751533286, -6.236658728205383),
    ("jakarta_gbk", 106.803, -6.2155),
    ("bundaran_hi", 106.8235, -6.19466),
    ("kelapa_gading", 106.910887, -6.1535777),
    ("jagakarsa", 106.80367, -6.35693),
    ("lubang_buaya", 106.90919, -6.28889),
    ("kebun_jeruk", 106.7525, -6.20737),
]


async def seed_stations():
    inserted = 0
    async with get_db_session() as db:
        for name, lon, lat in STATIONS:
            result = await db.execute(
                select(WeatherStation).filter(WeatherStation.name == name)
            )
            if result.scalars().first():
                continue
            db.add(
                WeatherStation(
                    name=name,
                    location=f"SRID=4326;POINT({lon} {lat})",
                )
            )
            inserted += 1
    logger.info(
        "[seed] stations: %s inserted, %s already existed.",
        inserted,
        len(STATIONS) - inserted,
    )


async def run_weather():
    logger.info("[seed] fetching weather data ...")
    await fetch_weather_data()


async def run_pm25():
    logger.info("[seed] crawling ISPU PM2.5 ...")
    await get_ispu_pm25_now()


async def main():
    args = set(sys.argv[1:])
    # Jika tidak ada argumen, jalankan hanya stations secara default untuk baseline
    run_all = False
    
    if "all" in args:
        run_all = True

    if run_all or "stations" in args or not args:
        await seed_stations()

    if run_all or "weather" in args:
        await run_weather()

    if run_all or "pm25" in args:
        await run_pm25()


if __name__ == "__main__":
    asyncio.run(main())
