import logging
import os
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from geoalchemy2.shape import to_shape

from apps.weather.models import PM25DataActual, WeatherData
from apps.weather.repositories import WeatherRepository

logger = logging.getLogger(__name__)

API_KEY = os.getenv("API_KEY")
BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
HTTP_OK = 200

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


class WeatherService:
    def __init__(self, repository: WeatherRepository):
        self.repository = repository

    async def fetch_and_save_weather(self):
        """Ambil data cuaca hari ini untuk semua stasiun."""
        stations = await self.repository.get_all_stations()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for station in stations:
                pt = to_shape(station.location)
                lat, lon = pt.y, pt.x
                name = station.name

                url = (
                    f"{BASE_URL}{lat},{lon}?unitGroup=metric&key={API_KEY}&include=days"
                )
                try:
                    response = await client.get(url)
                    if response.status_code == HTTP_OK:
                        data = response.json()
                        days = data.get("days", [])
                        if days:
                            day_data = days[0]
                            date_str = day_data.get("datetime")
                            if date_str:
                                date_obj = (
                                    datetime.strptime(date_str, "%Y-%m-%d")
                                    .replace(tzinfo=UTC)
                                    .date()
                                )
                                get_weather = (
                                    self.repository.get_weather_by_station_and_date
                                )
                                existing = await get_weather(station.id, date_obj)
                                if not existing:
                                    weather = self._make_weather_model(
                                        station.id, date_obj, day_data
                                    )
                                    await self.repository.save_weather(weather)
                                    logger.info(
                                        "[Created] %s | %s | Temp: %s",
                                        name,
                                        date_obj,
                                        weather.temperature,
                                    )
                                else:
                                    logger.info(
                                        "[Skipped] %s | %s already exists.",
                                        name,
                                        date_obj,
                                    )
                except Exception as e:
                    logger.error("[Fetch Failed] %s | Error: %s", name, e)

    async def crawl_and_save_pm25(self):
        """Scrape nilai ISPU PM2.5 terkini dan simpan ke database."""
        headers = {"User-Agent": "Mozilla/5.0"}

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
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

                    stasiun = await self.repository.get_station_by_name(
                        tempat["nama_tempat"]
                    )
                    if stasiun is None:
                        logger.warning(
                            "[Not Found] Station '%s' not in database.",
                            tempat["nama_tempat"],
                        )
                        continue

                    tanggal = datetime.now(UTC).date()
                    existing = (
                        await self.repository.get_pm25_actual_by_station_and_date(
                            stasiun.id, tanggal
                        )
                    )
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
                    await self.repository.save_pm25_actual(record)
                    logger.info(
                        "[Saved] %s | %s | PM2.5: %s",
                        tempat["nama_tempat"],
                        tanggal,
                        nilai_pm25,
                    )

                except Exception as e:
                    logger.error("[Error] %s: %s", tempat["nama_tempat"], e)

    def _make_weather_model(self, station_id, date_obj, day_data) -> WeatherData:
        return WeatherData(
            station_id=station_id,
            date=date_obj,
            temperature=day_data.get("temp"),
            temp_max=day_data.get("tempmax"),
            temp_min=day_data.get("tempmin"),
            feels_like=day_data.get("feelslike"),
            feels_like_max=day_data.get("feelslikemax"),
            feels_like_min=day_data.get("feelslikemin"),
            dew_point=day_data.get("dew"),
            humidity=day_data.get("humidity"),
            wind_speed=day_data.get("windspeed"),
            wind_gust=day_data.get("windgust"),
            wind_dir=day_data.get("winddir"),
            precipitation=day_data.get("precip"),
            precip_cover=day_data.get("precipcover"),
            barometric_pressure=day_data.get("pressure"),
            sea_level_pressure=day_data.get("sealevelpressure"),
            cloud_cover=day_data.get("cloudcover"),
            visibility=day_data.get("visibility"),
            uv_index=day_data.get("uvindex"),
            solar_radiation=day_data.get("solarradiation"),
            solar_energy=day_data.get("solarenergy"),
        )
