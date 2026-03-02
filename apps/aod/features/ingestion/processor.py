"""
AOD Ingestion
Processes downloaded .nc satellite files into GeoJSON polygons stored in PostGIS.
"""
import os
import math
import gc
from datetime import date, datetime

from pathlib import Path

import numpy as np
import xarray as xr
import rasterio
from rasterio.transform import from_bounds
import rioxarray
import geopandas as gpd
from shapely.geometry import box, MultiPolygon
from shapely.ops import unary_union

from apps.database import get_db_session
from apps.aod.models import Satellite, AerosolOpticalDepth, AerosolOpticalDepthPolygon

# Project root (4 levels up from this file: ingestion -> features -> aod -> apps -> backend)
_BASE_DIR = Path(__file__).resolve().parents[4]


# ---------------------------------------------------------------------------
# Coordinate / AOD conversion helpers
# ---------------------------------------------------------------------------

def convert_to_geoTiFF_input_data(nc_file_path, geotiff_file_path, geojson_filepath):
    """Parse a .nc file and return AOD grid data.

    Returns different structures depending on whether the source is VIIRS or Himawari.
    """
    print(nc_file_path)
    ds = xr.open_dataset(nc_file_path, decode_timedelta=False)
    folder_name = os.path.basename(os.path.dirname(nc_file_path))
    print(folder_name)

    # Batas wilayah Jakarta
    lat_min, lat_max = -6.5, -6.08
    lon_min, lon_max = 106.6, 107.0

    if folder_name == 'VIIRS':
        lat = ds['Latitude'].values
        lon = ds['Longitude'].values
        aod = ds['Aerosol_Optical_Thickness_550_Land_Ocean_Best_Estimate'].values

        aod = np.where(np.isnan(aod), -9999, aod)
        mask = (
            (lat >= lat_min) & (lat <= lat_max) &
            (lon >= lon_min) & (lon <= lon_max)
        )
        aod_filtered = np.full(aod.shape, 0, dtype=np.float32)
        aod_filtered[mask] = aod[mask]

        transform_region = from_bounds(
            lon.min(), lat.min(),
            lon.max(), lat.max(),
            lon.shape[1], lat.shape[0]
        )
        aod = np.flipud(aod_filtered)
        aod = np.fliplr(aod)
        return lat, lon, aod

    elif folder_name == 'Himawari':
        lat_min, lat_max = -6.35, -6.08
        lon_min, lon_max = 106.7, 106.95
        ds_subset = ds.sel(
            latitude=slice(lat_max, lat_min),
            longitude=slice(lon_min, lon_max)
        )
        print(ds_subset)
        if 'AOT_L2_Mean' not in ds_subset:
            raise ValueError("Data 'AOT_L2_Mean' tidak ditemukan dalam file.")

        aod = ds_subset['AOT_L2_Mean']
        latitude = ds_subset['latitude'].values
        longitude = ds_subset['longitude'].values
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
                        lon - lon_res / 2, lat - lat_res / 2,
                        lon + lon_res / 2, lat + lon_res / 2
                    )
                    records.append({'geometry': grid_cell, 'aod': float(val)})

        gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
        clipped_gdf = gpd.clip(gdf, jakarta)
        return latitude, longitude, aod_vals, clipped_gdf

    else:
        raise ValueError(f"Folder '{folder_name}' tidak dikenali sebagai 'VIIRS' atau 'Himawari'.")


# ---------------------------------------------------------------------------
# Himawari processing pipeline
# ---------------------------------------------------------------------------

def process_himawari_data():
    base_nc_folder_path = os.path.join(_BASE_DIR, 'data', 'Himawari')

    if not os.path.exists(base_nc_folder_path):
        return {"error": f"Folder {base_nc_folder_path} tidak ditemukan."}, 404

    jakarta_geojson = os.path.join(_BASE_DIR, 'id-jk.geojson')
    geotiff_folder = os.path.join(_BASE_DIR, 'data', 'geotiff_files')
    os.makedirs(geotiff_folder, exist_ok=True)

    processed_files = []
    errors = []

    try:
        with get_db_session() as db:
            satellite = db.query(Satellite).filter_by(satellite_name='Himawari').first()
            if satellite is None:
                satellite = Satellite(satellite_name='Himawari')
                db.add(satellite)
                db.commit()
                db.refresh(satellite)

            for nc_file_name in os.listdir(base_nc_folder_path):
                if not nc_file_name.endswith('.nc'):
                    continue
                nc_file_path = os.path.join(base_nc_folder_path, nc_file_name)
                filename_parts = nc_file_name.split('_')
                date_str = filename_parts[1]
                file_date = datetime.strptime(date_str, "%Y%m%d").date()
                geotiff_file_path = os.path.join(
                    geotiff_folder,
                    f"Himawari_{nc_file_name.replace('.nc', '.tif')}"
                )

                try:
                    latitude, longitude, aod_values, clipped_gdf = convert_to_geoTiFF_input_data(
                        nc_file_path, geotiff_file_path, jakarta_geojson
                    )
                    dataraster = []
                    for i in range(latitude.shape[0]):
                        for j in range(longitude.shape[0]):
                            lat_value = float(latitude[i])
                            lon_value = float(longitude[j])
                            aod_value = float(aod_values[i, j])
                            if math.isnan(aod_value):
                                aod_value = 0.0
                            dataraster.append({
                                "latitude": lat_value,
                                "longitude": lon_value,
                                "aod_values": aod_value
                            })

                    print(dataraster)
                    raster_data = AerosolOpticalDepth(
                        satellite_id=satellite.id,
                        data=dataraster,
                        date=file_date,
                    )
                    db.add(raster_data)
                    db.commit()
                    db.refresh(raster_data)

                    for _, row in clipped_gdf.iterrows():
                        geom = row.geometry
                        if geom.geom_type == 'MultiPolygon':
                            for poly in geom.geoms:
                                db.add(AerosolOpticalDepthPolygon(
                                    aod_id=raster_data.id,
                                    geom=f"SRID=4326;{poly.wkt}",
                                    aod_value=row['aod'],
                                    date=raster_data.date,
                                ))
                        else:
                            db.add(AerosolOpticalDepthPolygon(
                                aod_id=raster_data.id,
                                geom=f"SRID=4326;{geom.wkt}",
                                aod_value=row['aod'],
                                date=raster_data.date,
                            ))
                    db.commit()

                    if os.path.exists(geotiff_file_path):
                        os.remove(geotiff_file_path)
                    if os.path.exists(nc_file_path):
                        os.remove(nc_file_path)

                    processed_files.append(nc_file_name)

                except Exception as e:
                    db.rollback()
                    errors.append({nc_file_name: str(e)})

    except Exception as e:
        errors.append({"Himawari": str(e)})

    success = not errors
    return (
        {"processed_files": processed_files, "errors": errors if errors else "Semua file Himawari berhasil diproses."},
        200 if success else 206
    )


# ---------------------------------------------------------------------------
# VIIRS processing pipeline
# ---------------------------------------------------------------------------

def process_viirs_files():
    today = date.today()
    base_nc_folder_path = os.path.join(_BASE_DIR, 'data', 'VIIRS')
    jakarta_geojson = os.path.join(_BASE_DIR, 'id-jk.geojson')
    geotiff_folder = os.path.join(_BASE_DIR, 'data', 'geotiff_files')

    if not os.path.exists(base_nc_folder_path):
        return {
            "processed_files": [],
            "errors": [f"Folder {base_nc_folder_path} tidak ditemukan."]
        }

    os.makedirs(geotiff_folder, exist_ok=True)

    processed_files = []
    errors = []

    try:
        with get_db_session() as db:
            satellite = db.query(Satellite).filter_by(satellite_name='VIIRS').first()
            if satellite is None:
                satellite = Satellite(satellite_name='VIIRS')
                db.add(satellite)
                db.commit()
                db.refresh(satellite)

            for nc_file_name in os.listdir(base_nc_folder_path):
                if not nc_file_name.endswith('.nc'):
                    continue
                nc_file_path = os.path.join(base_nc_folder_path, nc_file_name)
                geotiff_file_path = os.path.join(
                    geotiff_folder,
                    f"VIIRS_{nc_file_name.replace('.nc', '.tif')}"
                )

                try:
                    latitude, longitude, aod_values = convert_to_geoTiFF_input_data(
                        nc_file_path, geotiff_file_path, jakarta_geojson
                    )
                    print(f"Longitude shape (VIIRS): {longitude.shape}")
                    print(f"Latitude shape (VIIRS): {latitude.shape}")

                    dataraster = []
                    for i in range(latitude.shape[0]):
                        for j in range(latitude.shape[1]):
                            lat_value = float(latitude[i, j])
                            lon_value = float(longitude[i, j])
                            aod_value = float(aod_values[i, j])
                            if math.isnan(aod_value):
                                aod_value = 0.0
                            dataraster.append({
                                "latitude": lat_value,
                                "longitude": lon_value,
                                "aod_values": aod_value
                            })

                    raster_data = AerosolOpticalDepth(
                        satellite_id=satellite.id,
                        data=dataraster,
                        date=today,
                    )
                    db.add(raster_data)
                    db.commit()
                    gc.collect()

                    if os.path.exists(geotiff_file_path):
                        os.remove(geotiff_file_path)
                        print(f"File {geotiff_file_path} berhasil dihapus.")
                    if os.path.exists(nc_file_path):
                        os.remove(nc_file_path)
                        print(f"File {nc_file_path} berhasil dihapus.")

                    processed_files.append(nc_file_name)

                except Exception as e:
                    db.rollback()
                    errors.append({nc_file_name: str(e)})

    except Exception as e:
        errors.append({"VIIRS": str(e)})

    return {
        "processed_files": processed_files,
        "errors": errors if errors else "Semua file VIIRS berhasil diproses."
    }
