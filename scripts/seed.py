import sys

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
    ("us_embassy_1",   106.8279877,  -6.1811056),
    ("us_embassy_2",   106.79319751533286,  -6.236658728205383),
    ("jakarta_gbk",    106.803,  -6.2155),
    ("bundaran_hi",    106.8235,  -6.19466),
    ("kelapa_gading",  106.910887,  -6.1535777),
    ("jagakarsa",      106.80367,  -6.35693),
    ("lubang_buaya",   106.90919,  -6.28889),
    ("kebun_jeruk",    106.7525,  -6.20737),
]


def seed_stations():
    from apps.database import get_db_session
    from apps.weather.models import WeatherStation

    with get_db_session() as db:
        inserted = 0
        for name, lon, lat in STATIONS:
            if db.query(WeatherStation).filter(WeatherStation.name == name).first():
                continue
            db.add(WeatherStation(
                name=name,
                location=f"SRID=4326;POINT({lon} {lat})",
            ))
            inserted += 1
        db.commit()
    print(f"[seed] stations: {inserted} inserted, {len(STATIONS) - inserted} already existed.")


def run_weather():
    from apps.weather.features.ingestion.weather_fetcher import fetch_weather_data
    print("[seed] fetching weather data ...")
    fetch_weather_data()


def run_pm25():
    from apps.weather.features.ingestion.pm25_crawler import get_ispu_pm25_now
    print("[seed] crawling ISPU PM2.5 ...")
    get_ispu_pm25_now()


if __name__ == "__main__":
    args = set(sys.argv[1:])
    run_all = not args

    if run_all or "stations" in args:
        seed_stations()

    if run_all or "weather" in args:
        run_weather()

    if run_all or "pm25" in args:
        run_pm25()
