from django.apps import AppConfig


class WeatherConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # Keep the same label as the original app for migration compatibility
    name = 'apps.weather'
    label = 'Weather_data'
    verbose_name = 'Weather & PM2.5 Ground Data'
