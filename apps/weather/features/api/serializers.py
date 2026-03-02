from rest_framework import serializers
from apps.weather.models import WeatherStation, WeatherData, pm25DataActual, pm25DataPrediction


class WeatherDataSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.name', read_only=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = WeatherData
        fields = [
            "temperature", "precipitation", "humidity",
            "wind_dir", "wind_speed",
            "station_name", "latitude", "longitude",
        ]

    def get_latitude(self, obj):
        return obj.station.location.y if obj.station and obj.station.location else None

    def get_longitude(self, obj):
        return obj.station.location.x if obj.station and obj.station.location else None


class WeatherStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherStation
        fields = '__all__'


class PM25ActualSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.name', read_only=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = pm25DataActual
        fields = '__all__'

    def get_latitude(self, obj):
        return obj.station.location.y if obj.station and obj.station.location else None

    def get_longitude(self, obj):
        return obj.station.location.x if obj.station and obj.station.location else None


class PM25PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = pm25DataPrediction
        fields = '__all__'


class WeatherDateInputSerializer(serializers.Serializer):
    date = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%Y-%m-%d"],
        help_text="Tanggal dengan format YYYY-MM-DD"
    )


class PM25DateInputSerializer(serializers.Serializer):
    date = serializers.DateField(
        format="%Y-%m-%d",
        input_formats=["%Y-%m-%d"],
        help_text="Tanggal dalam format YYYY-MM-DD"
    )
