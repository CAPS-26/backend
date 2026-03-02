from django.apps import AppConfig


class AodConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # Keep the same label as the original app for migration compatibility
    name = 'apps.aod'
    label = 'Aod_data'
    verbose_name = 'Aerosol Optical Depth'
