"""
Vertical Slice: Weather Ingestion
Imports historical PM2.5 data from Excel (.xls/.xlsx) files into the database.
Expected filename format: <station_name>_<YYYYMMDD>.xlsx
"""
import os
import pandas as pd
from datetime import datetime

from apps.database import get_db_session
from apps.weather.models import WeatherStation, PM25DataActual


def pm25ToDatabase(folder_path: str, kolom_nilai: str = 'ISPU PM2.5'):
    """Read Excel files from folder_path and save daily-average PM2.5 to the DB."""
    with get_db_session() as db:
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

                stasiun = (
                    db.query(WeatherStation)
                    .filter(WeatherStation.name.ilike(nama_stasiun.strip()))
                    .first()
                )
                if stasiun is None:
                    print(f"[Not Found] Station '{nama_stasiun}' not in database.")
                    continue

                record = PM25DataActual(
                    station_id=stasiun.id,
                    date=tanggal,
                    pm25_value=float(rata2),
                )
                db.add(record)
                db.commit()
                print(f"[Saved] {nama_stasiun} | {tanggal} | avg: {rata2:.2f}")

                try:
                    os.remove(full_path)
                    print(f"[Deleted] {file}")
                except Exception as e:
                    print(f"[Delete Error] {file}: {e}")

            except Exception as e:
                db.rollback()
                print(f"[Error] {file}: {e}")
