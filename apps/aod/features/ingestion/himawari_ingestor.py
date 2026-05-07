"""Ambil data AOD harian dari satelit Himawari via JAXA FTP."""

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from ftplib import FTP
from pathlib import Path

from apps.aod.features.ingestion.processor import process_himawari_data

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parents[4]
_DOWNLOAD_PATH = _BASE_DIR / "data" / "Himawari"


async def getDataHimawari():
    """Tugas async: unduh file .nc Himawari terbaru dan proses.

    Operasi FTP yang bersifat blocking dijalankan di thread agar event loop tidak
    terblokir.
    """
    ftp_user = os.getenv("USERHIMAWARI")
    ftp_password = os.getenv("PASSHIMAWARI")
    if not ftp_user or not ftp_password:
        logger.error("USERHIMAWARI or PASSHIMAWARI environment variables not set.")
        return

    today = datetime.now(UTC)
    year = today.year
    month = today.month
    yesterday = today - timedelta(days=1)

    _DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)

    ftp_host = "ftp.ptree.jaxa.jp"

    def _download_latest():
        try:
            with FTP(ftp_host) as ftp:
                ftp.login(ftp_user, ftp_password)
                logger.info(f"Logged in to FTP server: {ftp_host}")

                dir_data = f"pub/himawari/L3/ARP/031/{year}{month:02d}/daily"
                try:
                    ftp.cwd(dir_data)
                except Exception:
                    logger.warning(
                        "Directory %s not found, trying yesterday.", dir_data
                    )
                    dir_data = (
                        "pub/himawari/L3/ARP/031/"
                        f"{yesterday.year}{yesterday.month:02d}/daily"
                    )
                    ftp.cwd(dir_data)

                files = sorted(ftp.nlst())
                nc_files = [f for f in files if f.endswith(".nc")]

                if not nc_files:
                    logger.warning(f"No .nc files found in {dir_data}")
                    return None

                latest_file = nc_files[-1]
                local_file_path = _DOWNLOAD_PATH / latest_file

                if local_file_path.exists():
                    logger.info(f"File {latest_file} already exists locally. Skipping.")
                    return str(local_file_path)
                with local_file_path.open("wb") as local_file:
                    ftp.retrbinary(f"RETR {latest_file}", local_file.write)
                logger.info(
                    "File %s downloaded successfully to %s",
                    latest_file,
                    _DOWNLOAD_PATH,
                )
                return str(local_file_path)

        except Exception as e:
            logger.error(f"FTP error while accessing {ftp_host}: {e}")
            return None

    # Jalankan unduhan blocking di thread
    local_path = await asyncio.to_thread(_download_latest)
    if not local_path:
        return

    try:
        _result, status = await process_himawari_data()
        logger.info("Himawari processing status: %s", status)
    except Exception as e:
        logger.error("Error processing Himawari data: %s", e)
