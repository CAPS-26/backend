"""Enable PostGIS extensions and create all tables

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── PostGIS extensions ──────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_raster;")

    # ── AOD app tables ──────────────────────────────────────────────────────
    op.create_table(
        "aod_satellite",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("satellite_name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "aod_aerosolopticaldepth",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("satellite_id", sa.Integer(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["satellite_id"], ["aod_satellite.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "aod_polygon",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("aod_id", sa.Integer(), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="POLYGON", srid=4326),
            nullable=False,
        ),
        sa.Column("aod_value", sa.Float(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["aod_id"], ["aod_aerosolopticaldepth.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "aod_pm25estimate",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("aod_id", sa.Integer(), nullable=False),
        sa.Column("valuepm25", sa.JSON(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["aod_id"], ["aod_aerosolopticaldepth.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "aod_pm25polygon",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pm25_id", sa.Integer(), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="POLYGON", srid=4326),
            nullable=False,
        ),
        sa.Column("pm25_value", sa.Float(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["pm25_id"], ["aod_pm25estimate.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Weather app tables ──────────────────────────────────────────────────
    op.create_table(
        "weather_station",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "weather_data",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("temp_max", sa.Float(), nullable=True),
        sa.Column("temp_min", sa.Float(), nullable=True),
        sa.Column("feels_like", sa.Float(), nullable=True),
        sa.Column("feels_like_max", sa.Float(), nullable=True),
        sa.Column("feels_like_min", sa.Float(), nullable=True),
        sa.Column("dew_point", sa.Float(), nullable=True),
        sa.Column("humidity", sa.Float(), nullable=True),
        sa.Column("wind_speed", sa.Float(), nullable=True),
        sa.Column("wind_gust", sa.Float(), nullable=True),
        sa.Column("wind_dir", sa.Float(), nullable=True),
        sa.Column("precipitation", sa.Float(), nullable=True),
        sa.Column("precip_cover", sa.Float(), nullable=True),
        sa.Column("barometric_pressure", sa.Float(), nullable=True),
        sa.Column("sea_level_pressure", sa.Float(), nullable=True),
        sa.Column("cloud_cover", sa.Float(), nullable=True),
        sa.Column("visibility", sa.Float(), nullable=True),
        sa.Column("uv_index", sa.Float(), nullable=True),
        sa.Column("solar_radiation", sa.Float(), nullable=True),
        sa.Column("solar_energy", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["station_id"], ["weather_station.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "weather_pm25actual",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("pm25_value", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["station_id"], ["weather_station.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "weather_pm25prediction",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("pm25_value", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["station_id"], ["weather_station.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("weather_pm25prediction")
    op.drop_table("weather_pm25actual")
    op.drop_table("weather_data")
    op.drop_table("weather_station")
    op.drop_table("aod_pm25polygon")
    op.drop_table("aod_pm25estimate")
    op.drop_table("aod_polygon")
    op.drop_table("aod_aerosolopticaldepth")
    op.drop_table("aod_satellite")
