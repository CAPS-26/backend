"""
PM2.5 Estimation
Orchestrates the full estimation pipeline:
AOD grid data  +  nearest-station weather data  →  PM2.5 grid  →  PostGIS polygons
"""
import os
import csv
import math

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry

from apps.aod.models import AerosolOpticalDepth, pm25DataEstimate, PolygondataPM25
from apps.weather.models import WeatherData
from apps.aod.features.estimation.predictor import predict_model
from apps.aod.features.estimation.raster_converter import csv_to_geotiff, csvToPolygon

# Temporary CSV output directory (relative to BASE_DIR)
_TEMP_DIR = os.path.join(
    settings.BASE_DIR, 'apps', 'aod', 'features', 'estimation'
)


def _euclidean_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def estimatePm25():
    """Run PM2.5 spatial estimation for all unprocessed AOD records."""
    os.makedirs(_TEMP_DIR, exist_ok=True)
    rasterdata_all = AerosolOpticalDepth.objects.all()

    for rasterdata in rasterdata_all:
        aod_value = rasterdata.data
        aod_date = rasterdata.date

        if pm25DataEstimate.objects.filter(aodid=rasterdata).exists():
            print(f"[SKIP] PM2.5 estimate for AOD ID {rasterdata.id} already exists.")
            continue

        all_weather = WeatherData.objects.filter(date=aod_date).select_related('station')
        if not all_weather.exists():
            print(f"[WARNING] No weather data for {aod_date}, skipping AOD ID {rasterdata.id}.")
            continue

        all_stations = [
            {
                'station_id': w.station.id,
                'location_x': w.station.location.x,
                'location_y': w.station.location.y,
            }
            for w in all_weather
        ]

        merged_rows = []
        for aod in aod_value:
            aod_lon = aod['longitude']
            aod_lat = aod['latitude']
            aod_val = aod['aod_values']

            # Find nearest station using Euclidean distance on lat/lon
            nearest_station_id = min(
                all_stations,
                key=lambda s: _euclidean_distance(
                    aod_lat, aod_lon, s['location_y'], s['location_x']
                )
            )['station_id']

            weather_data = WeatherData.objects.filter(
                date=aod_date, station_id=nearest_station_id
            ).first()
            if not weather_data:
                continue

            merged_rows.append({
                'datetime': aod_date,
                'aod_longitude': aod_lon,
                'aod_latitude': aod_lat,
                'station_longitude': weather_data.station.location.x,
                'station_latitude': weather_data.station.location.y,
                'AOD': aod_val,
                'tempmax': weather_data.temp_max,
                'tempmin': weather_data.temp_min,
                'temp': weather_data.temperature,
                'feelslikemax': weather_data.feels_like_max,
                'feelslikemin': weather_data.feels_like_min,
                'feelslike': weather_data.feels_like,
                'dew': weather_data.dew_point,
                'humidity': weather_data.humidity,
                'precip': weather_data.precipitation,
                'precipcover': weather_data.precip_cover,
                'windgust': weather_data.wind_gust,
                'windspeed': weather_data.wind_speed,
                'winddir': weather_data.wind_dir,
                'sealevelpressure': weather_data.sea_level_pressure,
                'cloudcover': weather_data.cloud_cover,
                'visibility': weather_data.visibility,
                'solarradiation': weather_data.solar_radiation,
                'solarenergy': weather_data.solar_energy,
                'uvindex': weather_data.uv_index,
            })

        if not merged_rows:
            print(f"[WARNING] No merged data for AOD ID {rasterdata.id}, skipping.")
            continue

        # Write merged data to temporary CSV
        file_name = os.path.join(_TEMP_DIR, f'aod_data_{rasterdata.id}.csv')
        with open(file_name, mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=merged_rows[0].keys())
            writer.writeheader()
            writer.writerows(merged_rows)

        print(f"[INFO] AOD ID {rasterdata.id} saved to {file_name}")

        df = predict_model(file_name)
        print(df.shape, len(rasterdata.data))

        data = df.to_dict(orient="records")
        jakarta_geojson = os.path.join(settings.BASE_DIR, 'id-jk.geojson')
        polygondata = csvToPolygon(df, jakarta_geojson)

        pm25data = pm25DataEstimate.objects.create(
            aodid=rasterdata,
            valuepm25=data,
            date=rasterdata.date
        )

        for _, row in polygondata.iterrows():
            geom = row.geometry
            if geom.geom_type == 'MultiPolygon':
                for poly in geom.geoms:
                    polygon = GEOSGeometry(poly.wkt, srid=4326)
                    PolygondataPM25.objects.create(
                        pm25id=pm25data,
                        geom=polygon,
                        pm25_value=row['pm25'],
                        date=pm25data.date
                    )
            else:
                polygon = GEOSGeometry(geom.wkt, srid=4326)
                PolygondataPM25.objects.create(
                    pm25id=pm25data,
                    geom=polygon,
                    pm25_value=row['pm25'],
                    date=pm25data.date
                )

        print(f"[SUCCESS] PM2.5 estimation for AOD ID {rasterdata.id} saved.\n")

        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"Temp file {file_name} deleted.")
