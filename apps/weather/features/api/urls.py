from django.urls import path
from apps.weather.features.api.views import (
    LatestWeatherDataView,
    WeatherDataByDateView,
    LatestPM25ActualView,
    PM25ActualByDateView,
    LatestPM25PredictionView,
    PM25PredictionByDateView,
)

urlpatterns = [
    path('weather/', LatestWeatherDataView.as_view(), name='weather-latest'),
    path('weather/by-date/', WeatherDataByDateView.as_view(), name='weather-by-date'),
    path('pm25/actual/', LatestPM25ActualView.as_view(), name='pm25-actual-latest'),
    path('pm25/actual/by-date/', PM25ActualByDateView.as_view(), name='pm25-actual-by-date'),
    path('pm25/prediction/', LatestPM25PredictionView.as_view(), name='pm25-prediction-latest'),
    path('pm25/prediction/by-date/', PM25PredictionByDateView.as_view(), name='pm25-prediction-by-date'),
]
