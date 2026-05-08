"""Crawl nilai ISPU PM2.5 stasiun Jakarta dari portal pemerintah DKI."""

import asyncio
import logging
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import func, select

from apps.database import get_db_session
from apps.weather.models import PM25DataActual, WeatherStation

logger = logging.getLogger(__name__)

STATION_URLS = [
    {
        "url": "https://rendahemisi.jakarta.go.id/ispu-detail/1/us-embassy-1/",
        "nama_tempat": "us_embassy_1",
    },
    {
        "url": "https://rendahemisi.jakarta.go.id/ispu-detail/2/us-embassy-2/",
        "nama_tempat": "us_embassy_2",
    },
    {
        "url": "https://rendahemisi.jakarta.go.id/ispu-detail/3/jakarta-gbk/",
        "nama_tempat": "jakarta_gbk",
    },
    {
        "url": "https://rendahemisi.jakarta.go.id/ispu-detail/4/dki1-bundaran-hi/",
        "nama_tempat": "bundaran_hi",
    },
    {
        "url": "https://rendahemisi.jakarta.go.id/ispu-detail/5/dki2-kelapa-gading/",
        "nama_tempat": "kelapa_gading",
    },
    {
        "url": "https://rendahemisi.jakarta.go.id/ispu-detail/6/dki3-jagakarsa/",
        "nama_tempat": "jagakarsa",
    },
    {
        "url": "https://rendahemisi.jakarta.go.id/ispu-detail/7/dki4-lubang-buaya/",
        "nama_tempat": "lubang_buaya",
    },
    {
        "url": "https://rendahemisi.jakarta.go.id/ispu-detail/8/dki5-kebun-jeruk/",
        "nama_tempat": "kebun_jeruk",
    },
]


async def get_ispu_pm25_now():
    """Scrape nilai ISPU PM2.5 terkini dan simpan ke database secara paralel."""
    headers = {"User-Agent": "Mozilla/5.0"}
    tanggal = datetime.now(UTC).date()

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # 1. Ambil data dari semua URL secara paralel
        tasks = [client.get(t["url"]) for t in STATION_URLS]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    async with get_db_session() as db:
        # 2. Ambil semua stasiun sekaligus
        station_names = [t["nama_tempat"] for t in STATION_URLS]
        result_stations = await db.execute(
            select(WeatherStation).filter(
                func.lower(WeatherStation.name).in_([n.lower() for n in station_names])
            )
        )
        stations_map = {s.name.lower(): s for s in result_stations.scalars().all()}

        # 3. Ambil data existing untuk tanggal hari ini sekaligus (N+1 fix)
        station_ids = [s.id for s in stations_map.values()]
        if station_ids:
            result_existing = await db.execute(
                select(PM25DataActual.station_id).where(
                    PM25DataActual.station_id.in_(station_ids),
                    PM25DataActual.date == tanggal,
                )
            )
            existing_station_ids = set(result_existing.scalars().all())
        else:
            existing_station_ids = set()

        # 4. Proses hasil respon
        for tempat, response in zip(STATION_URLS, responses):
            if isinstance(response, Exception) or response.status_code != 200:
                logger.error("[Error] %s: Fetch failed.", tempat["nama_tempat"])
                continue

            try:
                soup = BeautifulSoup(response.text, "html.parser")
                nilai_pm25 = None
                for box_icon in soup.find_all("div", class_="feature-box-icon"):
                    p_tag = box_icon.find("p")
                    if p_tag and "PM 2.5" in p_tag.text:
                        h5_tag = box_icon.find("h5")
                        if h5_tag:
                            nilai_pm25 = h5_tag.text.strip()
                            break

                val_float = float(nilai_pm25) if nilai_pm25 else 0.0
                name_lower = tempat["nama_tempat"].lower()
                stasiun = stations_map.get(name_lower)

                if not stasiun:
                    logger.warning("[Not Found] %s", tempat["nama_tempat"])
                    continue

                if stasiun.id in existing_station_ids:
                    logger.info(
                        "[Skipped] %s | %s already exists.", stasiun.name, tanggal
                    )
                    continue

                # Tambahkan record baru
                db.add(
                    PM25DataActual(
                        station_id=stasiun.id,
                        date=tanggal,
                        pm25_value=val_float,
                    )
                )
                logger.info("[Saved] %s | PM2.5: %s", stasiun.name, val_float)

            except Exception as e:
                logger.error("[Error] %s: %s", tempat["nama_tempat"], e)

        # get_db_session akan melakukan commit otomatis
