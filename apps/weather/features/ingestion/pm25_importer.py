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
    """Baca file Excel dari folder_path dan simpan rata-rata PM2.5 harian ke DB."""
    base_path = Path(folder_path)
    async with get_db_session() as db:
        for file_path in await asyncio.to_thread(_list_files, base_path):
            if file_path.suffix not in {".xls", ".xlsx"}:
                continue
            try:
                parts = file_path.stem.split("_")
                nama_stasiun = "_".join(parts[:-1])
                tanggal_str = parts[-1]
                tanggal = (
                    datetime.strptime(tanggal_str, "%Y%m%d").replace(tzinfo=UTC).date()
                )

                df = pd.read_excel(file_path)

                if kolom_nilai not in df.columns:
                    logger.warning(
                        "Column '%s' not found in %s", kolom_nilai, file_path.name
                    )
                    continue

                df[kolom_nilai] = pd.to_numeric(df[kolom_nilai], errors="coerce")
                rata2 = df[kolom_nilai].mean()

                result = await db.execute(
                    select(WeatherStation).filter(
                        WeatherStation.name.ilike(nama_stasiun.strip())
                    )
                )
                stasiun = result.scalars().first()
                if stasiun is None:
                    logger.warning(
                        "[Not Found] Station '%s' not in database.", nama_stasiun
                    )
                    continue

                record = PM25DataActual(
                    station_id=stasiun.id,
                    date=tanggal,
                    pm25_value=float(rata2),
                )
                db.add(record)
                await db.commit()
                logger.info("[Saved] %s | %s | avg: %.2f", nama_stasiun, tanggal, rata2)

                try:
                    file_path.unlink()
                    logger.info("[Deleted] %s", file_path.name)
                except Exception as e:
                    logger.warning("[Delete Error] %s: %s", file_path.name, e)

            except Exception as e:
                await db.rollback()
                logger.error("[Error] %s: %s", file_path.name, e)


async def pm25ToDatabase(folder_path: str, kolom_nilai: str = "ISPU PM2.5"):
    """Entrypoint async untuk impor file Excel PM2.5.

    Gunakan coroutine ini saat dipanggil dari konteks async (scheduler).
    Untuk penggunaan CLI, panggil `pm25ToDatabase_sync` yang menjalankan
    coroutine di event loop baru.
    """
    await _pm25_to_database(folder_path, kolom_nilai)


def pm25ToDatabase_sync(folder_path: str, kolom_nilai: str = "ISPU PM2.5"):
    """Wrapper sinkron untuk kompatibilitas CLI."""
    asyncio.run(_pm25_to_database(folder_path, kolom_nilai))
