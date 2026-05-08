"""Import data PM2.5 historis dari file Excel (.xls/.xlsx) ke database.
Format nama file: <nama_stasiun>_<YYYYMMDD>.xlsx
"""

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from apps.database import get_db_session
from apps.weather.models import PM25DataActual, WeatherStation

logger = logging.getLogger(__name__)


def _list_files(base_path: Path) -> list[Path]:
    return list(base_path.iterdir())


async def _pm25_to_database(folder_path: str, kolom_nilai: str = "ISPU PM2.5"):
    """Baca file Excel dari folder_path dan simpan rata-rata PM2.5 harian ke DB secara efisien."""
    base_path = Path(folder_path)
    if not base_path.exists():
        return

    files = [f for f in base_path.iterdir() if f.suffix in {".xls", ".xlsx"}]
    if not files:
        return

    async with get_db_session() as db:
        # Pre-fetch stations to avoid N+1
        result_stations = await db.execute(select(WeatherStation))
        stations_map = {s.name.lower(): s for s in result_stations.scalars().all()}

        for file_path in files:
            try:
                parts = file_path.stem.split("_")
                if len(parts) < 2:
                    continue
                nama_stasiun = "_".join(parts[:-1]).lower()
                tanggal_str = parts[-1]
                tanggal = (
                    datetime.strptime(tanggal_str, "%Y%m%d").replace(tzinfo=UTC).date()
                )

                # Baca excel (blocking, jalankan di thread)
                df = await asyncio.to_thread(pd.read_excel, file_path)

                if kolom_nilai not in df.columns:
                    logger.warning(
                        "Column '%s' not found in %s", kolom_nilai, file_path.name
                    )
                    continue

                df[kolom_nilai] = pd.to_numeric(df[kolom_nilai], errors="coerce")
                rata2 = df[kolom_nilai].mean()
                if pd.isna(rata2):
                    rata2 = 0.0

                stasiun = stations_map.get(nama_stasiun)
                if stasiun is None:
                    logger.warning(
                        "[Not Found] Station '%s' not in database.", nama_stasiun
                    )
                    continue

                # Cek existing
                result_existing = await db.execute(
                    select(PM25DataActual).filter_by(
                        station_id=stasiun.id, date=tanggal
                    )
                )
                if result_existing.scalars().first():
                    logger.info(
                        "[Skipped] %s | %s already exists.", stasiun.name, tanggal
                    )
                    continue

                db.add(
                    PM25DataActual(
                        station_id=stasiun.id,
                        date=tanggal,
                        pm25_value=float(rata2),
                    )
                )
                logger.info("[Saved] %s | %s | avg: %.2f", stasiun.name, tanggal, rata2)

                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning("[Delete Error] %s: %s", file_path.name, e)

            except Exception as e:
                logger.error("[Error] %s: %s", file_path.name, e)

        # get_db_session akan melakukan commit otomatis


async def pm25ToDatabase(folder_path: str, kolom_nilai: str = "ISPU PM2.5"):
    """Entrypoint async untuk impor file Excel PM2.5."""
    await _pm25_to_database(folder_path, kolom_nilai)


def pm25ToDatabase_sync(folder_path: str, kolom_nilai: str = "ISPU PM2.5"):
    """Wrapper sinkron untuk kompatibilitas CLI."""
    asyncio.run(_pm25_to_database(folder_path, kolom_nilai))
