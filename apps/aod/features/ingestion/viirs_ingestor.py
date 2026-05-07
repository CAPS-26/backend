"""Ambil data AOD dari satelit VIIRS via NASA EarthAccess."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import earthaccess

from apps.aod.features.ingestion.processor import process_viirs_files

_BASE_DIR = Path(__file__).resolve().parents[4]
_DOWNLOAD_PATH = _BASE_DIR / "data" / "VIIRS"


async def retrieve_viirs_data():
    today = datetime.now(tz=UTC)
    yesterday = today - timedelta(days=3)

    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    _DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)

    def _download():
        earthaccess.login(strategy="netrc")
        results = earthaccess.search_data(
            short_name="AERDB_L2_VIIRS_SNPP",
            bounding_box=(106.66, -6.5, 107.1, -6.08),
            temporal=(yesterday_str, today_str),
        )
        return earthaccess.download(results, str(_DOWNLOAD_PATH))

    # Jalankan unduhan earthaccess yang blocking di thread
    await asyncio.to_thread(_download)
    await process_viirs_files()
