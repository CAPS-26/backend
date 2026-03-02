from django.contrib import admin
from apps.aod.models import Satellite, AerosolOpticalDepth, AerosolOpticalDepthPolygon, pm25DataEstimate, PolygondataPM25

admin.site.register(Satellite)
admin.site.register(AerosolOpticalDepth)
admin.site.register(AerosolOpticalDepthPolygon)
admin.site.register(pm25DataEstimate)
admin.site.register(PolygondataPM25)
