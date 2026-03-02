from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from apps.database import Base


class WeatherStation(Base):
    __tablename__ = "weather_station"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)

    weather_data = relationship("WeatherData", back_populates="station")
    pm25_actual = relationship("PM25DataActual", back_populates="station")
    pm25_prediction = relationship("PM25DataPrediction", back_populates="station")


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(Integer, ForeignKey("weather_station.id"), nullable=False)
    date = Column(Date, nullable=False)
    temperature = Column(Float, nullable=True)
    temp_max = Column(Float, nullable=True)
    temp_min = Column(Float, nullable=True)
    feels_like = Column(Float, nullable=True)
    feels_like_max = Column(Float, nullable=True)
    feels_like_min = Column(Float, nullable=True)
    dew_point = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    wind_gust = Column(Float, nullable=True)
    wind_dir = Column(Float, nullable=True)
    precipitation = Column(Float, nullable=True)
    precip_cover = Column(Float, nullable=True)
    barometric_pressure = Column(Float, nullable=True)
    sea_level_pressure = Column(Float, nullable=True)
    cloud_cover = Column(Float, nullable=True)
    visibility = Column(Float, nullable=True)
    uv_index = Column(Float, nullable=True)
    solar_radiation = Column(Float, nullable=True)
    solar_energy = Column(Float, nullable=True)

    station = relationship("WeatherStation", back_populates="weather_data")


class PM25DataActual(Base):
    __tablename__ = "weather_pm25actual"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(Integer, ForeignKey("weather_station.id"), nullable=False)
    date = Column(Date, nullable=True)
    pm25_value = Column(Float, nullable=True)

    station = relationship("WeatherStation", back_populates="pm25_actual")


class PM25DataPrediction(Base):
    __tablename__ = "weather_pm25prediction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(Integer, ForeignKey("weather_station.id"), nullable=False)
    date = Column(Date, nullable=False)
    pm25_value = Column(Float, nullable=True)

    station = relationship("WeatherStation", back_populates="pm25_prediction")

