"""
Signal invalidation cache untuk data peta (destination GeoJSON).

Saat staff mengubah data destinasi/wahana/bundle/parking/kategori/desa/kecamatan,
cache GeoJSON langsung dibuang supaya data baru muncul TANPA restart / reload
khusus. Chatbot response TIDAK ikut di-cache (bergantung user/session/tanggal).
"""

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save

from apps.gis.models import (
    ParkingFee,
    TicketBundle,
    TourismCategory,
    TouristDestination,
    Wahana,
)
from apps.master.models import District, Village

GEOJSON_CACHE_KEY = "gis:destination_geojson"

_CACHE_RELATED_MODELS = [
    TouristDestination,
    Wahana,
    TicketBundle,
    ParkingFee,
    TourismCategory,
    Village,
    District,
]


def _invalidate_geojson(sender, **kwargs):
    cache.delete(GEOJSON_CACHE_KEY)


def connect_signals():
    for model in _CACHE_RELATED_MODELS:
        post_save.connect(_invalidate_geojson, sender=model, weak=False)
        post_delete.connect(_invalidate_geojson, sender=model, weak=False)
