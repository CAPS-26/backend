from django.contrib import admin
from apps.weather.models import WeatherStation, WeatherData, pm25DataActual, pm25DataPrediction

admin.site.register(WeatherStation)
admin.site.register(WeatherData)
admin.site.register(pm25DataActual)
admin.site.register(pm25DataPrediction)
