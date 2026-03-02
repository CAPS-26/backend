import json
from datetime import date, timedelta

from django.core.serializers import serialize
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from apps.aod.models import AerosolOpticalDepthPolygon, PolygondataPM25
from apps.aod.features.api.serializers import DateInputSerializer


class GetAodPolygonView(APIView):
    @swagger_auto_schema(
        operation_summary="Ambil Data Polygon AOD Kemarin",
        operation_description="Mengembalikan data polygon AOD (Aerosol Optical Depth) untuk kemarin.",
        responses={200: "Berhasil", 404: "Data tidak ditemukan", 500: "Kesalahan server"}
    )
    def get(self, request):
        try:
            yesterday = date.today() - timedelta(days=1)
            polygons = AerosolOpticalDepthPolygon.objects.filter(date=yesterday)
            if not polygons.exists():
                return Response(
                    {"message": "Tidak ada data polygon untuk tanggal kemarin."},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = serialize("geojson", polygons, geometry_field="geom", fields=["aod_value"])
            return Response(json.loads(serializer), status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAodPolygonByDateView(APIView):
    @swagger_auto_schema(
        request_body=DateInputSerializer,
        operation_summary="Ambil Data Polygon AOD Berdasarkan Tanggal",
        operation_description="Mengembalikan data polygon AOD berdasarkan tanggal yang diberikan (YYYY-MM-DD).",
        responses={200: "Berhasil", 404: "Data tidak ditemukan", 400: "Input tidak valid"}
    )
    def post(self, request):
        serializer = DateInputSerializer(data=request.data)
        if serializer.is_valid():
            tanggal = serializer.validated_data['tanggal']
            polygons = AerosolOpticalDepthPolygon.objects.filter(date=tanggal)
            if not polygons.exists():
                return Response(
                    {"message": "Tidak ada data polygon untuk tanggal tersebut."},
                    status=status.HTTP_404_NOT_FOUND
                )
            geojson_data = serialize("geojson", polygons, geometry_field="geom", fields=["aod_value"])
            return Response(json.loads(geojson_data), status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetPM25PolygonView(APIView):
    @swagger_auto_schema(
        operation_summary="Ambil Data Polygon PM2.5 Kemarin",
        operation_description="Mengembalikan data polygon PM2.5 estimasi untuk kemarin.",
        responses={200: "Berhasil", 404: "Data tidak ditemukan", 500: "Kesalahan server"}
    )
    def get(self, request):
        try:
            yesterday = date.today() - timedelta(days=1)
            polygons = PolygondataPM25.objects.filter(date=yesterday)
            if not polygons.exists():
                return Response(
                    {"message": "Tidak ada data polygon untuk tanggal kemarin."},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = serialize("geojson", polygons, geometry_field="geom", fields=["pm25_value"])
            return Response(json.loads(serializer), status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetPM25PolygonByDateView(APIView):
    @swagger_auto_schema(
        request_body=DateInputSerializer,
        operation_summary="Ambil Data Polygon PM2.5 Berdasarkan Tanggal",
        operation_description="Mengembalikan data polygon PM2.5 estimasi berdasarkan tanggal (YYYY-MM-DD).",
        responses={200: "Berhasil", 404: "Data tidak ditemukan", 400: "Input tidak valid"}
    )
    def post(self, request):
        serializer = DateInputSerializer(data=request.data)
        if serializer.is_valid():
            tanggal = serializer.validated_data['tanggal']
            polygons = PolygondataPM25.objects.filter(date=tanggal)
            if not polygons.exists():
                return Response(
                    {"message": "Tidak ada data polygon untuk tanggal tersebut."},
                    status=status.HTTP_404_NOT_FOUND
                )
            geojson_data = serialize("geojson", polygons, geometry_field="geom", fields=["pm25_value"])
            return Response(json.loads(geojson_data), status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
