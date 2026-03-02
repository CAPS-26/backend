from django.contrib.gis.db import models

class WeatherStation(models.Model):
    name = models.CharField(max_length=255)
    location = models.PointField() 
    def __str__(self):
        return self.name

class WeatherData(models.Model):
    station = models.ForeignKey(WeatherStation, on_delete=models.CASCADE, related_name='weather_data')
    date = models.DateField()
    temperature = models.FloatField(null=True, blank=True)  
    temp_max = models.FloatField(null=True, blank=True)  
    temp_min = models.FloatField(null=True, blank=True)  
    feels_like = models.FloatField(null=True, blank=True)  
    feels_like_max = models.FloatField(null=True, blank=True)  
    feels_like_min = models.FloatField(null=True, blank=True)  
    dew_point = models.FloatField(null=True, blank=True)  
    humidity = models.FloatField(null=True, blank=True)  
    wind_speed = models.FloatField(null=True, blank=True) 
    wind_gust = models.FloatField(null=True, blank=True)
    wind_dir = models.FloatField(null=True, blank=True) 
    precipitation = models.FloatField(null=True, blank=True)  
    precip_cover = models.FloatField(null=True, blank=True)  
    barometric_pressure = models.FloatField(null=True, blank=True) 
    sea_level_pressure = models.FloatField(null=True, blank=True)  
    cloud_cover = models.FloatField(null=True, blank=True)
    visibility = models.FloatField(null=True, blank=True)
    uv_index = models.FloatField(null=True, blank=True)
    solar_radiation = models.FloatField(null=True, blank=True)
    solar_energy = models.FloatField(null=True, blank=True)
    def __str__(self):
        return f"{self.station.name} - {self.date}"
    
class pm25DataActual(models.Model):
    station = models.ForeignKey(WeatherStation, on_delete=models.CASCADE, related_name='pm25data_actual')
    date = models.DateField(null=True, blank=True)
    pm25_value = models.FloatField(null=True, blank=True)

class pm25DataPrediction(models.Model):
    station = models.ForeignKey(WeatherStation, on_delete=models.CASCADE, related_name='pm25data_prediction')
    date = models.DateField()
    pm25_value = models.FloatField(null=True, blank=True)

