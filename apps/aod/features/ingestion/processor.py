"""Proses file .nc satelit menjadi polygon GeoJSON dan simpan ke PostGIS."""

import gc
import logging
import math
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
import xarray as xr
from shapely.geometry import box
from sqlalchemy import select

from apps.aod.models import AerosolOpticalDepth, AerosolOpticalDepthPolygon, Satellite
from apps.database import get_db_session

# Root proyek (5 level ke atas: ingestion→features→aod→apps→root)
_BASE_DIR = Path(__file__).resolve().parents[4]
logger = logging.getLogger(__name__)


# Helper konversi koordinat dan AOD


def convert_to_geoTiFF_input_data(nc_file_path, geojson_filepath):
    """Baca file .nc dan kembalikan data grid AOD.

    Struktur berbeda untuk VIIRS dan Himawari.
    """
    logger.debug("Processing file: %s", nc_file_path)
    ds = xr.open_dataset(nc_file_path, decode_timedelta=False)
    folder_name = Path(nc_file_path).parent.name
    logger.debug("Detected folder: %s", folder_name)

    # Batas wilayah Jakarta
    lat_min, lat_max = -6.5, -6.08
    lon_min, lon_max = 106.6, 107.0

    if folder_name == "VIIRS":
        lat = ds["Latitude"].values
        lon = ds["Longitude"].values
        aod = ds["Aerosol_Optical_Thickness_550_Land_Ocean_Best_Estimate"].values

        aod = np.where(np.isnan(aod), -9999, aod)
        mask = (lat >= lat_min) & (lat <= lat_max) & (lon >= lon_min) & (lon <= lon_max)
        aod_filtered = np.full(aod.shape, 0, dtype=np.float32)
        aod_filtered[mask] = aod[mask]

        aod = np.flipud(aod_filtered)
        aod = np.fliplr(aod)
        return lat, lon, aod

    if folder_name == "Himawari":
        lat_min, lat_max = -6.35, -6.08
        lon_min, lon_max = 106.7, 106.95
        ds_subset = ds.sel(
            latitude=slice(lat_max, lat_min), longitude=slice(lon_min, lon_max)
        )
        logger.debug("Himawari subset shape: %s", ds_subset)
        if "AOT_L2_Mean" not in ds_subset:
            raise ValueError("Data 'AOT_L2_Mean' tidak ditemukan dalam file.")

        aod = ds_subset["AOT_L2_Mean"]
        latitude = ds_subset["latitude"].values
        longitude = ds_subset["longitude"].values
        aod_vals = aod.values

        jakarta = gpd.read_file(geojson_filepath).to_crs("EPSG:4326")

        lat_res = 0.05
        lon_res = 0.05

        records = []
        for i, lat in enumerate(latitude):
            for j, lon in enumerate(longitude):
                val = aod_vals[i, j]
                if not np.isnan(val):
                    grid_cell = box(
                        lon - lon_res / 2,
                        lat - lat_res / 2,
                        lon + lon_res / 2,
                        lat + lon_res / 2,
                    )
                    records.append({"geometry": grid_cell, "aod": float(val)})

        gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
        clipped_gdf = gpd.clip(gdf, jakarta)
        return latitude, longitude, aod_vals, clipped_gdf

    raise ValueError(
        f"Folder '{folder_name}' tidak dikenali sebagai 'VIIRS' atau 'Himawari'."
    )


# Pipeline Himawari


async def _process_himawari_data():  # noqa: PLR0912, PLR0915
    base_nc_folder_path = _BASE_DIR / "data" / "Himawari"

    if not base_nc_folder_path.exists():
        return {"error": f"Folder {base_nc_folder_path} tidak ditemukan."}, 404

    jakarta_geojson = _BASE_DIR / "id-jk.geojson"
    geotiff_folder = _BASE_DIR / "data" / "geotiff_files"
    geotiff_folder.mkdir(parents=True, exist_ok=True)

    processed_files = []
    errors = []

    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(Satellite).filter_by(satellite_name="Himawari")
            )
            satellite = result.scalars().first()
            if satellite is None:
                satellite = Satellite(satellite_name="Himawari")
                db.add(satellite)
                await db.commit()
                await db.refresh(satellite)

            for nc_path in base_nc_folder_path.iterdir():
                if nc_path.suffix != ".nc":
                    continue
                nc_name = nc_path.name
                nc_file_path = nc_path
                filename_parts = nc_path.name.split("_")
                date_str = filename_parts[1]
                file_date = (
                    datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=UTC).date()
                )
                geotiff_file_path = (
                    geotiff_folder / f"Himawari_{nc_path.name.replace('.nc', '.tif')}"
                )

                try:
                    latitude, longitude, aod_values, clipped_gdf = (
                        convert_to_geoTiFF_input_data(
                            str(nc_file_path),
                            str(jakarta_geojson),
                        )
                    )
                    dataraster = []
                    for i in range(latitude.shape[0]):
                        for j in range(longitude.shape[0]):
                            lat_value = float(latitude[i])
                            lon_value = float(longitude[j])
                            aod_value = float(aod_values[i, j])
                            if math.isnan(aod_value):
                                aod_value = 0.0
                            dataraster.append(
                                {
                                    "latitude": lat_value,
                                    "longitude": lon_value,
                                    "aod_values": aod_value,
                                }
                            )

                    logger.debug("Raster item count: %s", len(dataraster))
                    raster_data = AerosolOpticalDepth(
                        satellite_id=satellite.id,
                        data=dataraster,
                        date=file_date,
                    )
                    db.add(raster_data)
                    await db.commit()
                    await db.refresh(raster_data)

                    polygons_to_add = []
                    for _, row in clipped_gdf.iterrows():
                        geom = row.geometry
                        if geom.geom_type == "MultiPolygon":
                            for poly in geom.geoms:
                                polygons_to_add.append(
                                    AerosolOpticalDepthPolygon(
                                        aod_id=raster_data.id,
                                        geom=f"SRID=4326;{poly.wkt}",
                                        aod_value=row["aod"],
                                        date=raster_data.date,
                                    )
                                )
                        else:
                            polygons_to_add.append(
                                AerosolOpticalDepthPolygon(
                                    aod_id=raster_data.id,
                                    geom=f"SRID=4326;{geom.wkt}",
                                    aod_value=row["aod"],
                                    date=raster_data.date,
                                )
                            )
                    if polygons_to_add:
                        db.add_all(polygons_to_add)
                    await db.commit()

                    if geotiff_file_path.exists():
                        geotiff_file_path.unlink()
                    if nc_file_path.exists():
                        nc_file_path.unlink()

                    processed_files.append(nc_name)

                except Exception as e:
                    await db.rollback()
                    errors.append({nc_name: str(e)})

    except Exception as e:
        errors.append({"Himawari": str(e)})

    success = not errors
    return (
        {
            "processed_files": processed_files,
            "errors": errors if errors else "Semua file Himawari berhasil diproses.",
        },
        200 if success else 206,
    )


async def process_himawari_data():
    """Wrapper async untuk memproses file Himawari.

    Mengembalikan payload yang sama dengan versi asli.
    """
    return await _process_himawari_data()


# Pipeline VIIRS


async def _process_viirs_files():
    today = datetime.now(tz=UTC).date()
    base_nc_folder_path = _BASE_DIR / "data" / "VIIRS"
    jakarta_geojson = _BASE_DIR / "id-jk.geojson"
    geotiff_folder = _BASE_DIR / "data" / "geotiff_files"

    if not base_nc_folder_path.exists():
        return {
            "processed_files": [],
            "errors": [f"Folder {base_nc_folder_path} tidak ditemukan."],
        }

    geotiff_folder.mkdir(parents=True, exist_ok=True)

    processed_files = []
    errors = []

    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(Satellite).filter_by(satellite_name="VIIRS")
            )
            satellite = result.scalars().first()
            if satellite is None:
                satellite = Satellite(satellite_name="VIIRS")
                db.add(satellite)
                await db.commit()
                await db.refresh(satellite)

            for nc_path in base_nc_folder_path.iterdir():
                if nc_path.suffix != ".nc":
                    continue
                nc_name = nc_path.name
                nc_file_path = nc_path
                geotiff_file_path = (
                    geotiff_folder / f"VIIRS_{nc_path.name.replace('.nc', '.tif')}"
                )

                try:
                    latitude, longitude, aod_values = convert_to_geoTiFF_input_data(
                        str(nc_file_path),
                        str(jakarta_geojson),
                    )
                    logger.debug("Longitude shape (VIIRS): %s", longitude.shape)
                    logger.debug("Latitude shape (VIIRS): %s", latitude.shape)

                    dataraster = []
                    for i in range(latitude.shape[0]):
                        for j in range(latitude.shape[1]):
                            lat_value = float(latitude[i, j])
                            lon_value = float(longitude[i, j])
                            aod_value = float(aod_values[i, j])
                            if math.isnan(aod_value):
                                aod_value = 0.0
                            dataraster.append(
                                {
                                    "latitude": lat_value,
                                    "longitude": lon_value,
                                    "aod_values": aod_value,
                                }
                            )

                    raster_data = AerosolOpticalDepth(
                        satellite_id=satellite.id,
                        data=dataraster,
                        date=today,
                    )
                    db.add(raster_data)
                    await db.commit()
                    gc.collect()

                    if geotiff_file_path.exists():
                        geotiff_file_path.unlink()
                        logger.debug("File %s berhasil dihapus.", geotiff_file_path)
                    if nc_file_path.exists():
                        nc_file_path.unlink()
                        logger.debug("File %s berhasil dihapus.", nc_file_path)

                    processed_files.append(nc_name)

                except Exception as e:
                    await db.rollback()
                    errors.append({nc_name: str(e)})

    except Exception as e:
        errors.append({"VIIRS": str(e)})

    return {
        "processed_files": processed_files,
        "errors": errors if errors else "Semua file VIIRS berhasil diproses.",
    }


async def process_viirs_files():
    """Wrapper async untuk memproses file VIIRS."""
    return await _process_viirs_files()
