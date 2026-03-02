"""
Vertical Slice: Weather Ingestion
Scheduled job that pulls daily weather data from Visual Crossing API
and stores it in the WeatherData table.
"""
import requests
import logging
import os
from datetime import datetime, date, timedelta

from apps.weather.models import WeatherData, WeatherStation

API_KEY = os.getenv("API_KEY")
BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"

logger = logging.getLogger(__name__)


def fetch_weather_data():
    """Fetch today's weather for all stations."""
    stations = WeatherStation.objects.all()

    for station in stations:
        lat = station.location.y
        lon = station.location.x
        name = station.name

        url = f"{BASE_URL}{lat},{lon}?unitGroup=metric&key={API_KEY}&include=days"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            days = data.get('days', [])

            if days:
                day_data = days[0]
                date_str = day_data.get('datetime')
                if date_str:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

                    if not WeatherData.objects.filter(station=station, date=date_obj).exists():
                        weather = WeatherData.objects.create(
                            station=station,
                            date=date_obj,
                            temperature=day_data.get('temp'),
                            temp_max=day_data.get('tempmax'),
                            temp_min=day_data.get('tempmin'),
                            feels_like=day_data.get('feelslike'),
                            feels_like_max=day_data.get('feelslikemax'),
                            feels_like_min=day_data.get('feelslikemin'),
                            dew_point=day_data.get('dew'),
                            humidity=day_data.get('humidity'),
                            wind_speed=day_data.get('windspeed'),
                            wind_gust=day_data.get('windgust'),
                            wind_dir=day_data.get('winddir'),
                            precipitation=day_data.get('precip'),
                            precip_cover=day_data.get('precipcover'),
                            barometric_pressure=day_data.get('pressure'),
                            sea_level_pressure=day_data.get('sealevelpressure'),
                            cloud_cover=day_data.get('cloudcover'),
                            visibility=day_data.get('visibility'),
                            uv_index=day_data.get('uvindex'),
                            solar_radiation=day_data.get('solarradiation'),
                            solar_energy=day_data.get('solarenergy')
                        )
                        logger.info(f"[Created] {name} | {date_obj} | Temp: {weather.temperature}")
                    else:
                        logger.info(f"[Skipped] {name} | {date_obj} already exists.")
                else:
                    logger.warning(f"[Missing Date] {name}")
            else:
                logger.warning(f"[No Data] {name}")
        else:
            logger.warning(f"[Fetch Failed] {name} | Status Code: {response.status_code}")


def fetch_weather_data_range(days_back: int = 3):
    """Fetch weather for a range of days (backfill)."""
    results = []
    stations = WeatherStation.objects.all()
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)

    for station in stations:
        lat = station.location.y
        lon = station.location.x
        name = station.name

        url = f"{BASE_URL}{lat},{lon}/{start_date}/{end_date}?unitGroup=metric&key={API_KEY}&include=days"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            days = data.get('days', [])

            for day_data in days:
                date_str = day_data.get('datetime')
                if not date_str:
                    continue
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

                if not WeatherData.objects.filter(station=station, date=date_obj).exists():
                    weather = WeatherData.objects.create(
                        station=station,
                        date=date_obj,
                        temperature=day_data.get('temp'),
                        temp_max=day_data.get('tempmax'),
                        temp_min=day_data.get('tempmin'),
                        feels_like=day_data.get('feelslike'),
                        feels_like_max=day_data.get('feelslikemax'),
                        feels_like_min=day_data.get('feelslikemin'),
                        dew_point=day_data.get('dew'),
                        humidity=day_data.get('humidity'),
                        wind_speed=day_data.get('windspeed'),
                        wind_gust=day_data.get('windgust'),
                        wind_dir=day_data.get('winddir'),
                        precipitation=day_data.get('precip'),
                        precip_cover=day_data.get('precipcover'),
                        barometric_pressure=day_data.get('pressure'),
                        sea_level_pressure=day_data.get('sealevelpressure'),
                        cloud_cover=day_data.get('cloudcover'),
                        visibility=day_data.get('visibility'),
                        uv_index=day_data.get('uvindex'),
                        solar_radiation=day_data.get('solarradiation'),
                        solar_energy=day_data.get('solarenergy')
                    )
                    results.append({"station": name, "date": date_obj, "status": "Created"})
                else:
                    results.append({"station": name, "date": date_obj, "status": "Skipped"})
        else:
            results.append({"station": name, "error": f"Fetch failed: {response.status_code}"})

    return results
