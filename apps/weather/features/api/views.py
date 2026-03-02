from datetime import date

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.weather.models import WeatherData, WeatherStation, pm25DataActual, pm25DataPrediction
from apps.weather.features.api.serializers import (
    WeatherDataSerializer,
    PM25ActualSerializer,
    PM25PredictionSerializer,
    WeatherDateInputSerializer,
    PM25DateInputSerializer,
)


class LatestWeatherDataView(APIView):
    @swagger_auto_schema(
        operation_summary="Ambil Data Cuaca Hari Ini",
        operation_description="Mengembalikan data cuaca berdasarkan tanggal hari ini.",
        responses={
            200: WeatherDataSerializer(many=True),
            404: openapi.Response(description="Tidak ada data cuaca untuk tanggal hari ini."),
        }
    )
    def get(self, request):
        today = date.today()
        weather_data = WeatherData.objects.filter(date=today)
        if not weather_data.exists():
            return Response(
                {"message": f"Tidak ada data cuaca untuk tanggal {today}."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = WeatherDataSerializer(weather_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WeatherDataByDateView(APIView):
    @swagger_auto_schema(
        operation_summary="Ambil Data Cuaca Berdasarkan Tanggal",
        operation_description="Mengembalikan data cuaca berdasarkan tanggal yang diberikan (YYYY-MM-DD).",
        request_body=WeatherDateInputSerializer,
        responses={
            200: WeatherDataSerializer(many=True),
            400: openapi.Response(description="Input tanggal tidak valid."),
            404: openapi.Response(description="Tidak ada data cuaca untuk tanggal yang diminta."),
        }
    )
    def post(self, request):
        serializer = WeatherDateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        input_date = serializer.validated_data['date']
        weather_data = WeatherData.objects.filter(date=input_date)
        if not weather_data.exists():
            return Response(
                {"message": f"Tidak ada data cuaca untuk tanggal {input_date}."},
                status=status.HTTP_404_NOT_FOUND
            )
        result_serializer = WeatherDataSerializer(weather_data, many=True)
        return Response(result_serializer.data, status=status.HTTP_200_OK)


class LatestPM25ActualView(APIView):
    @swagger_auto_schema(
        operation_summary="Ambil Data PM2.5 Aktual Hari Ini",
        operation_description="Mengembalikan data PM2.5 aktual dari seluruh stasiun untuk tanggal hari ini.",
        responses={
            200: PM25ActualSerializer(many=True),
            404: openapi.Response(description="Tidak ada data PM2.5 untuk tanggal hari ini."),
        }
    )
    def get(self, request):
        today = date.today()
        data_today = pm25DataActual.objects.select_related('station').filter(date=today)
        if not data_today.exists():
            return Response(
                {"message": f"Tidak ada data PM2.5 untuk tanggal {today}."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = PM25ActualSerializer(data_today, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PM25ActualByDateView(APIView):
    @swagger_auto_schema(
        operation_summary="Ambil Data PM2.5 Aktual Berdasarkan Tanggal",
        operation_description="Mengembalikan data PM2.5 aktual berdasarkan tanggal (YYYY-MM-DD).",
        request_body=PM25DateInputSerializer,
        responses={
            200: PM25ActualSerializer(many=True),
            400: openapi.Response(description="Input tanggal tidak valid."),
            404: openapi.Response(description="Tidak ada data PM2.5 untuk tanggal yang diminta."),
        }
    )
    def post(self, request):
        serializer = PM25DateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        input_date = serializer.validated_data['date']
        data = pm25DataActual.objects.select_related('station').filter(date=input_date)
        if not data.exists():
            return Response(
                {"message": f"Tidak ada data PM2.5 untuk tanggal {input_date}."},
                status=status.HTTP_404_NOT_FOUND
            )
        result_serializer = PM25ActualSerializer(data, many=True)
        return Response(result_serializer.data, status=status.HTTP_200_OK)


class LatestPM25PredictionView(APIView):
    @swagger_auto_schema(
        operation_summary="Ambil Data PM2.5 Prediksi Hari Ini",
        operation_description="Mengembalikan data PM2.5 prediksi dari seluruh stasiun untuk tanggal hari ini.",
        responses={
            200: PM25PredictionSerializer(many=True),
            404: openapi.Response(description="Tidak ada data PM2.5 prediksi untuk tanggal hari ini."),
        }
    )
    def get(self, request):
        today = date.today()
        data_today = pm25DataPrediction.objects.select_related('station').filter(date=today)
        if not data_today.exists():
            return Response(
                {"message": f"Tidak ada data PM2.5 prediksi untuk tanggal {today}."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = PM25PredictionSerializer(data_today, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PM25PredictionByDateView(APIView):
    @swagger_auto_schema(
        operation_summary="Ambil Data PM2.5 Prediksi Berdasarkan Tanggal",
        operation_description="Mengembalikan data PM2.5 prediksi berdasarkan tanggal (YYYY-MM-DD).",
        request_body=PM25DateInputSerializer,
        responses={
            200: PM25PredictionSerializer(many=True),
            400: openapi.Response(description="Input tanggal tidak valid."),
            404: openapi.Response(description="Tidak ada data PM2.5 prediksi untuk tanggal yang diminta."),
        }
    )
    def post(self, request):
        serializer = PM25DateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        input_date = serializer.validated_data['date']
        data = pm25DataPrediction.objects.select_related('station').filter(date=input_date)
        if not data.exists():
            return Response(
                {"message": f"Tidak ada data PM2.5 prediksi untuk tanggal {input_date}."},
                status=status.HTTP_404_NOT_FOUND
            )
        result_serializer = PM25PredictionSerializer(data, many=True)
        return Response(result_serializer.data, status=status.HTTP_200_OK)
