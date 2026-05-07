"""Crawl nilai ISPU PM2.5 stasiun Jakarta dari portal pemerintah DKI."""

import logging
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

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
    """Scrape nilai ISPU PM2.5 terkini dan simpan ke database."""
    headers = {"User-Agent": "Mozilla/5.0"}

    async with (
        httpx.AsyncClient(headers=headers, timeout=30.0) as client,
        get_db_session() as db,
    ):
        for tempat in STATION_URLS:
            try:
                res = await client.get(tempat["url"])
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")

                nilai_pm25 = None
                for box_icon in soup.find_all("div", class_="feature-box-icon"):
                    p_tag = box_icon.find("p")
                    if p_tag and "PM 2.5" in p_tag.text:
                        h5_tag = box_icon.find("h5")
                        if h5_tag:
                            nilai_pm25 = h5_tag.text.strip()
                            break

                if nilai_pm25 is None:
                    nilai_pm25 = 0.0

                # Cari stasiun
                result = await db.execute(
                    select(WeatherStation).filter(
                        WeatherStation.name.ilike(tempat["nama_tempat"].strip())
                    )
                )
                stasiun = result.scalars().first()

                if stasiun is None:
                    logger.warning(
                        "[Not Found] Station '%s' not in database.",
                        tempat["nama_tempat"],
                    )
                    continue

                tanggal = datetime.now(UTC).date()

                # Cek existing
                result = await db.execute(
                    select(PM25DataActual).filter_by(
                        station_id=stasiun.id, date=tanggal
                    )
                )
                existing = result.scalars().first()

                if existing:
                    logger.info(
                        "[Skipped] %s | %s already exists.",
                        tempat["nama_tempat"],
                        tanggal,
                    )
                    continue

                record = PM25DataActual(
                    station_id=stasiun.id,
                    date=tanggal,
                    pm25_value=float(nilai_pm25),
                )
                db.add(record)
                await db.commit()
                logger.info(
                    "[Saved] %s | %s | PM2.5: %s",
                    tempat["nama_tempat"],
                    tanggal,
                    nilai_pm25,
                )
            except Exception as e:
                logger.error("[Error] %s: %s", tempat["nama_tempat"], e)
                await db.rollback()
