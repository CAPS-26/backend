"""Seed 30 days of weather + AOD + PM2.5 historical data from external APIs."""

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from ftplib import FTP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from sqlalchemy import func, select

from apps.aod.features.ingestion.processor import process_himawari_data
from apps.aod.models import AerosolOpticalDepth
from apps.database import get_db_session
from apps.weather.features.ingestion.weather_fetcher import _make_weather
from apps.weather.models import PM25DataActual, WeatherData, WeatherStation
from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
logger = logging.getLogger("backfill")

API_KEY = settings.api_key
BASE_WEATHER_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
DOWNLOAD_DIR = Path(__file__).resolve().parents[1] / "data" / "Himawari"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

FTP_HOST = "ftp.ptree.jaxa.jp"
FTP_USER = os.getenv("USERHIMAWARI", "")
FTP_PASS = os.getenv("PASSHIMAWARI", "")
DAYS = 30

WEEKDAY_NAMES = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
    4: "Friday", 5: "Saturday", 6: "Sunday",
}


async def backfill_weather_day(db, stations, target_date: datetime):
    date_str = target_date.strftime("%Y-%m-%d")
    async with httpx.AsyncClient(timeout=30.0) as client:
        new_count = 0
        for name, lat, lon in stations:
            url = f"{BASE_WEATHER_URL}{lat},{lon}/{date_str}?unitGroup=metric&key={API_KEY}&include=days"
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("  Weather [%s] HTTP %d", name, resp.status_code)
                    continue
                data = resp.json()
                for day_data in data.get("days", []):
                    day_date = datetime.strptime(day_data["datetime"], "%Y-%m-%d").date()
                    stmt = select(WeatherStation).where(WeatherStation.name == name)
                    r = await db.execute(stmt)
                    station = r.scalars().first()
                    if not station:
                        continue
                    existing = await db.execute(
                        select(WeatherData).where(
                            WeatherData.station_id == station.id,
                            WeatherData.date == day_date,
                        )
                    )
                    if existing.scalars().first():
                        continue
                    db.add(_make_weather(station.id, day_date, day_data))
                    new_count += 1
                    await db.commit()
            except Exception as e:
                logger.warning("  Weather [%s] %s", name, e)
        if new_count:
            logger.info("  Weather %s: %d new", date_str, new_count)
        else:
            logger.info("  Weather %s: 0 new", date_str)


def _download_himawari_date(target_date: datetime):
    y, m = target_date.year, target_date.month
    target_str = target_date.strftime("%Y%m%d")
    dir_data = f"pub/himawari/L3/ARP/031/{y}{m:02d}/daily"
    try:
        with FTP(FTP_HOST, timeout=30) as ftp:
            ftp.login(FTP_USER, FTP_PASS)
            ftp.cwd(dir_data)
            files = sorted(f for f in ftp.nlst() if f.endswith(".nc"))
            if not files:
                return None
            matching = [f for f in files if target_str in f]
            chosen = matching[0] if matching else files[-1]
            local_path = DOWNLOAD_DIR / chosen
            if local_path.exists():
                return str(local_path)
            with local_path.open("wb") as lf:
                ftp.retrbinary(f"RETR {chosen}", lf.write)
            logger.info("  Downloaded Himawari: %s", chosen)
            return str(local_path)
    except Exception as e:
        logger.warning("  Himawari [%s] %s", target_str, e)
        return None


async def backfill_aod_day(db, target_date: datetime):
    try:
        local_file = await asyncio.to_thread(_download_himawari_date, target_date)
        if local_file:
            await process_himawari_data(Path(local_file), target_date)
            r = await db.execute(
                select(func.count()).select_from(AerosolOpticalDepth).where(
                    AerosolOpticalDepth.date == target_date.date()
                )
            )
            logger.info("  AOD %s: %d records", target_date.strftime("%Y-%m-%d"), r.scalar())
        else:
            logger.info("  AOD %s: no file", target_date.strftime("%Y-%m-%d"))
    except Exception as e:
        logger.warning("  AOD %s: %s", target_date.strftime("%Y-%m-%d"), e)


async def backfill_pm25_day(db, target_date: datetime):
    date_str = target_date.strftime("%d-%m-%Y")
    url = f"https://ispu.menlhk.go.id/apimobile/v1/ambangBatasWilayah?tanggal={date_str}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={"Accept": "application/json"})
            if resp.status_code != 200:
                logger.warning("  PM2.5 [%s] HTTP %d", date_str, resp.status_code)
                return
            data = resp.json()
            if not data or (isinstance(data, dict) and data.get("status") == "error"):
                logger.info("  PM2.5 [%s]: no data", date_str)
                return
            r = await db.execute(select(WeatherStation))
            station_map = {s.name: s.id for s in r.scalars().all()}
            count = 0
            items = data if isinstance(data, list) else [data]
            for item in items:
                name = (item.get("nama") or "").lower().replace(" ", "_")
                if name not in station_map:
                    continue
                pm_val = item.get("pm25") or item.get("pm25_value")
                if pm_val is None:
                    continue
                sid = station_map[name]
                existing = await db.execute(
                    select(PM25DataActual).where(
                        PM25DataActual.station_id == sid,
                        PM25DataActual.date == target_date.date(),
                    )
                )
                if existing.scalars().first():
                    continue
                db.add(PM25DataActual(station_id=sid, date=target_date.date(), pm25_value=float(pm_val)))
                count += 1
            await db.commit()
            logger.info("  PM2.5 [%s]: %d records", date_str, count)
    except Exception as e:
        logger.warning("  PM2.5 [%s]: %s", date_str, e)


async def main():
    today = datetime.now(tz=UTC)
    async with get_db_session() as db:
        r = await db.execute(
            select(WeatherStation.name,
                   func.ST_Y(WeatherStation.location).label("lat"),
                   func.ST_X(WeatherStation.location).label("lon"))
        )
        stations = [(r[0], float(r[1]), float(r[2])) for r in r.all()]
        logger.info("Stations=%d, backfilling %d days...", len(stations), DAYS)

        for i in range(DAYS, 0, -1):
            d = today - timedelta(days=i)
            logger.info("Day %d/%d: %s", DAYS - i + 1, DAYS, d.strftime("%Y-%m-%d"))
            await backfill_weather_day(db, stations, d)
            await backfill_aod_day(db, d)
            await backfill_pm25_day(db, d)
            await asyncio.sleep(0.5)

        for label, model in [("Weather", WeatherData), ("PM2.5", PM25DataActual), ("AOD", AerosolOpticalDepth)]:
            r = await db.execute(select(func.count()).select_from(model))
            logger.info("FINAL %s: %d records", label, r.scalar())
        logger.info("DONE")


if __name__ == "__main__":
    asyncio.run(main())
