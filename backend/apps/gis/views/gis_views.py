from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

from common.models.decorators import staff_required

from apps.gis.models import TouristDestination
from apps.gis.services.geo_service import GeoJSONService


def explore_page(request):
    """
    Landing visitor — asisten wisata + peta + destinasi (publik, tanpa login).
    """
    destinations = list(
        TouristDestination.objects
        .filter(is_active=True)
        .select_related("village", "district", "village__district")
        .prefetch_related("categories", "wahanas", "bundles", "parking_fees")
        .order_by("name")[:8]
    )

    return render(
        request,
        "gis/explore.html",
        {
            "destinations": destinations,
        },
    )


def map_page(request):
    """
    Halaman peta wisata — Leaflet + GeoJSON.

    Publik (tanpa login) — berisi marker destinasi wisata. Layer yang
    berisi data riset (clustering/skor desa) dipisah ke endpoint staff-only.
    """

    return render(
        request,
        "gis/map.html",
        {
            "data_status": GeoJSONService.data_status(),
        },
    )


def destinations_page(request):
    """
    Daftar destinasi wisata (read-only) — publik.
    """

    destinations = (
        TouristDestination.objects
        .filter(is_active=True)
        .select_related("village", "district", "village__district")
        .prefetch_related("categories")
        .order_by("name")
    )

    return render(
        request,
        "gis/destinations.html",
        {
            "destinations": destinations,
        },
    )


@staff_required
def village_geojson(request):
    return JsonResponse(GeoJSONService.village_geojson())


@staff_required
def village_points_geojson(request):
    return JsonResponse(GeoJSONService.village_points_geojson())


def destination_geojson(request):
    return JsonResponse(GeoJSONService.destination_geojson())


def elevation_zones_geojson(request):
    """Layer zona ketinggian (region-level) untuk peta."""
    features, _ = GeoJSONService.load_features_from(
        settings.GIS_ELEVATION_GEOJSON_PATH
    )
    return JsonResponse({"type": "FeatureCollection", "features": features})


def characteristic_zones_geojson(request):
    """Layer karakteristik wilayah (region-level, per kecamatan) untuk peta."""
    features, _ = GeoJSONService.load_features_from(
        settings.GIS_CHARACTERISTIC_GEOJSON_PATH
    )
    return JsonResponse({"type": "FeatureCollection", "features": features})


@staff_required
def legend(request):
    return JsonResponse(GeoJSONService.legend())
