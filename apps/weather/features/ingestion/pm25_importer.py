"""
Vertical Slice: Weather Ingestion
Imports historical PM2.5 data from Excel (.xls/.xlsx) files into the database.
Expected filename format: <station_name>_<YYYYMMDD>.xlsx
"""
import os
import pandas as pd
from datetime import datetime

from apps.weather.models import WeatherStation, pm25DataActual


def pm25ToDatabase(folder_path: str, kolom_nilai: str = 'ISPU PM2.5'):
    """Read Excel files from folder_path and save daily-average PM2.5 to the DB."""
    for file in os.listdir(folder_path):
        if not (file.endswith('.xls') or file.endswith('.xlsx')):
            continue
        try:
            filename = os.path.splitext(file)[0]
            parts = filename.split('_')
            nama_stasiun = '_'.join(parts[:-1])
            tanggal_str = parts[-1]
            tanggal = datetime.strptime(tanggal_str, "%Y%m%d").date()

            full_path = os.path.join(folder_path, file)
            df = pd.read_excel(full_path)

            if kolom_nilai not in df.columns:
                print(f"Column '{kolom_nilai}' not found in {file}")
                continue

            df[kolom_nilai] = pd.to_numeric(df[kolom_nilai], errors='coerce')
            rata2 = df[kolom_nilai].mean()

            try:
                stasiun = WeatherStation.objects.get(name__iexact=nama_stasiun.strip())
                pm25DataActual.objects.create(
                    station=stasiun,
                    date=tanggal,
                    pm25_value=rata2
                )
                print(f"[Saved] {nama_stasiun} | {tanggal} | avg: {rata2:.2f}")
            except WeatherStation.DoesNotExist:
                print(f"[Not Found] Station '{nama_stasiun}' not in database.")

            try:
                os.remove(full_path)
                print(f"[Deleted] {file}")
            except Exception as e:
                print(f"[Delete Error] {file}: {e}")

        except Exception as e:
            print(f"[Error] {file}: {e}")
