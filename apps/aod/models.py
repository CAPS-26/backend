from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from apps.database import Base


class Satellite(Base):
    __tablename__ = "aod_satellite"

    id = Column(Integer, primary_key=True, autoincrement=True)
    satellite_name = Column(String(255), nullable=False)

    aod_records = relationship("AerosolOpticalDepth", back_populates="satellite")


class AerosolOpticalDepth(Base):
    __tablename__ = "aod_aerosolopticaldepth"

    id = Column(Integer, primary_key=True, autoincrement=True)
    satellite_id = Column(Integer, ForeignKey("aod_satellite.id"), nullable=True)
    data = Column(JSON, nullable=False)
    date = Column(Date, nullable=False)

    satellite = relationship("Satellite", back_populates="aod_records")
    aod_polygons = relationship("AerosolOpticalDepthPolygon", back_populates="aod")
    pm25_estimates = relationship("PM25DataEstimate", back_populates="aod")


class AerosolOpticalDepthPolygon(Base):
    __tablename__ = "aod_polygon"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aod_id = Column(Integer, ForeignKey("aod_aerosolopticaldepth.id"), nullable=False)
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    aod_value = Column(Float, nullable=False)
    date = Column(Date, nullable=False)

    aod = relationship("AerosolOpticalDepth", back_populates="aod_polygons")


class PM25DataEstimate(Base):
    __tablename__ = "aod_pm25estimate"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aod_id = Column(Integer, ForeignKey("aod_aerosolopticaldepth.id"), nullable=False)
    valuepm25 = Column(JSON, nullable=False)
    date = Column(Date, nullable=False)

    aod = relationship("AerosolOpticalDepth", back_populates="pm25_estimates")
    pm25_polygons = relationship("PolygonDataPM25", back_populates="pm25_estimate")


class PolygonDataPM25(Base):
    __tablename__ = "aod_pm25polygon"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pm25_id = Column(Integer, ForeignKey("aod_pm25estimate.id"), nullable=False)
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    pm25_value = Column(Float, nullable=False)
    date = Column(Date, nullable=False)

    pm25_estimate = relationship("PM25DataEstimate", back_populates="pm25_polygons")
