from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers

from apps.aod.models import AerosolOpticalDepthPolygon, PolygondataPM25


class DateInputSerializer(serializers.Serializer):
    tanggal = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d'])


class AodPolygonSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = AerosolOpticalDepthPolygon
        geo_field = "geom"
        fields = ["aod_value"]


class PM25PolygonSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = PolygondataPM25
        geo_field = "geom"
        fields = ["pm25_value"]
