"""
Vertical Slice: Weather Ingestion
Crawls ISPU PM2.5 readings for Jakarta stations from the DKI Jakarta government portal.
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from apps.database import get_db_session
from apps.weather.models import WeatherStation, PM25DataActual

STATION_URLS = [
    {"url": "https://rendahemisi.jakarta.go.id/ispu-detail/1/us-embassy-1/", "nama_tempat": "us_embassy_1"},
    {"url": "https://rendahemisi.jakarta.go.id/ispu-detail/2/us-embassy-2/", "nama_tempat": "us_embassy_2"},
    {"url": "https://rendahemisi.jakarta.go.id/ispu-detail/3/jakarta-gbk/", "nama_tempat": "jakarta_gbk"},
    {"url": "https://rendahemisi.jakarta.go.id/ispu-detail/4/dki1-bundaran-hi/", "nama_tempat": "bundaran_hi"},
    {"url": "https://rendahemisi.jakarta.go.id/ispu-detail/5/dki2-kelapa-gading/", "nama_tempat": "kelapa_gading"},
    {"url": "https://rendahemisi.jakarta.go.id/ispu-detail/6/dki3-jagakarsa/", "nama_tempat": "jagakarsa"},
    {"url": "https://rendahemisi.jakarta.go.id/ispu-detail/7/dki4-lubang-buaya/", "nama_tempat": "lubang_buaya"},
    {"url": "https://rendahemisi.jakarta.go.id/ispu-detail/8/dki5-kebun-jeruk/", "nama_tempat": "kebun_jeruk"},
]


def get_ispu_pm25_now():
    """Scrape current PM2.5 ISPU values and persist them to the database."""
    headers = {"User-Agent": "Mozilla/5.0"}

    with get_db_session() as db:
        for tempat in STATION_URLS:
            try:
                res = requests.get(tempat["url"], headers=headers)
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

                try:
                    stasiun = (
                        db.query(WeatherStation)
                        .filter(WeatherStation.name.ilike(tempat['nama_tempat'].strip()))
                        .first()
                    )
                    if stasiun is None:
                        print(f"[Not Found] Station '{tempat['nama_tempat']}' not in database.")
                        continue

                    tanggal = datetime.now().date()
                    record = PM25DataActual(
                        station_id=stasiun.id,
                        date=tanggal,
                        pm25_value=float(nilai_pm25),
                    )
                    db.add(record)
                    db.commit()
                    print(f"[Saved] {tempat['nama_tempat']} | {tanggal} | PM2.5: {nilai_pm25}")

                except Exception as inner_e:
                    db.rollback()
                    print(f"[DB Error] {tempat['nama_tempat']}: {inner_e}")

            except Exception as e:
                print(f"[Error] {tempat['nama_tempat']}: {e}")
