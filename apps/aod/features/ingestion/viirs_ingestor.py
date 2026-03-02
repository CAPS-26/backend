"""
VIIRS Ingestion
Retrieves AOD data from VIIRS satellite via NASA EarthAccess.
"""
import earthaccess
import os
from datetime import datetime, timedelta

from apps.aod.features.ingestion.processor import process_viirs_files


def retrieve_viirs_data():
    today = datetime.today()
    yesterday = today - timedelta(days=3)

    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    download_path = os.path.join(base_dir, '..', '..', '..', '..', 'data', 'VIIRS')
    download_path = os.path.normpath(download_path)
    os.makedirs(download_path, exist_ok=True)

    auth = earthaccess.login(strategy="netrc")

    results = earthaccess.search_data(
        short_name='AERDB_L2_VIIRS_SNPP',
        bounding_box=(106.66, -6.5, 107.1, -6.08),
        temporal=(yesterday_str, today_str)
    )

    print(download_path)
    files = earthaccess.download(results, download_path)
    process_viirs_files()
