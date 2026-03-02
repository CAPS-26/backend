-- Enable the raster extension (split from core PostGIS since version 3.0).
-- This must run before Django migrations that use RasterField.
CREATE EXTENSION IF NOT EXISTS postgis_raster;
