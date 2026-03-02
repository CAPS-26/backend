-- Enable PostGIS and the raster extension (split from core PostGIS since version 3.0).
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
