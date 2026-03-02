from django.urls import path
from apps.aod.features.api.views import (
    GetAodPolygonView,
    GetAodPolygonByDateView,
    GetPM25PolygonView,
    GetPM25PolygonByDateView,
)

urlpatterns = [
    path('polygon/', GetAodPolygonView.as_view(), name='aod-polygon'),
    path('polygon/by-date/', GetAodPolygonByDateView.as_view(), name='aod-polygon-by-date'),
    path('pm25/polygon/', GetPM25PolygonView.as_view(), name='pm25-polygon'),
    path('pm25/polygon/by-date/', GetPM25PolygonByDateView.as_view(), name='pm25-polygon-by-date'),
]
