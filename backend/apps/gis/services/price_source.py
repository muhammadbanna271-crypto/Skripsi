"""
Pengambilan harga tiket dari sumber eksternal (Tahap 5).

Prinsip penting (dari requirement):

- PRIORITASKAN API / akses resmi, bukan scraping rapuh.
- JANGAN bergantung pada satu website saja.
- Kalau gagal / tidak ditemukan, sistem TETAP berjalan normal: harga
  terakhir yang valid dipertahankan, dan staff bisa input manual.

Provider diregistrasi ke ``PRICE_PROVIDERS``. Saat ini hanya ada
``GooglePlacesProvider`` — dan perlu dicatat JUJUR: Google Places API
TIDAK menyediakan harga tiket destinasi wisata (hanya ``price_level``
skala 0-4, bukan Rupiah), jadi provider ini hampir selalu menghasilkan
"belum tersedia". Provider nyata lain (website resmi / Traveloka dsb.)
tinggal didaftarkan di sini bila sudah punya API/akses resmi.
"""

import logging

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

PLACES_TEXT_SEARCH_URL = (
    "https://maps.googleapis.com/maps/api/place/textsearch/json"
)
PLACES_DETAILS_URL = (
    "https://maps.googleapis.com/maps/api/place/details/json"
)


class GooglePlacesProvider:
    """
    Provider resmi Google Places (hanya aktif bila ``GOOGLE_MAPS_API_KEY``
    di-set di settings/.env). Tidak mengembalikan harga tiket karena Places
    API tidak menyediakannya — hanya dipakai sebagai contoh titik integrasi
    sumber eksternal yang aman (API resmi, bukan scraping).
    """

    name = "Google Places"

    @classmethod
    def fetch(cls, destination):
        key = getattr(settings, "GOOGLE_MAPS_API_KEY", "")
        if not key:
            return None

        query = destination.name
        if destination.village_id and destination.village is not None:
            query = f"{query} {destination.village.name}"

        try:
            response = requests.get(
                PLACES_TEXT_SEARCH_URL,
                params={"query": f"{query} Kota Batu", "key": key},
                timeout=15,
            )
            if response.status_code != 200:
                return None

            results = response.json().get("results") or []
            if not results:
                return None

            place_id = results[0].get("place_id")
            if not place_id:
                return None

            details = requests.get(
                PLACES_DETAILS_URL,
                params={
                    "place_id": place_id,
                    "fields": "price_level,formatted_address",
                    "key": key,
                },
                timeout=15,
            ).json()
        except requests.RequestException as error:
            logger.warning("Google Places request gagal: %s", error)
            return None

        result = details.get("result") or {}

        # Places API tidak menyediakan harga tiket (price_level hanyalah
        # indikator kelas harga 0-4). Jangan dipaksa jadi harga Rupiah.
        _ = result
        return None


# Daftar provider eksternal (urutan = prioritas). Kosongkan bila belum ada
# sumber resmi; sistem otomatis fallback ke input manual.
PRICE_PROVIDERS = [
    GooglePlacesProvider,
]


class PriceSourceService:
    """
    Ambil harga terbaru dari provider eksternal dengan fallback aman.

    ``update_destination`` TIDAK pernah menimpa harga terakhir yang valid
    bila update gagal/tidak tersedia — sesuai requirement caching/update.
    """

    @classmethod
    def update_destination(cls, destination):
        for provider in PRICE_PROVIDERS:
            try:
                price = provider.fetch(destination)
            except Exception as error:  # pragma: no cover - defensive
                logger.warning(
                    "Price provider %s gagal: %s", provider.name, error
                )
                price = None

            if price is not None:
                applied = cls._apply(destination, price, provider.name)
                if applied:
                    return {
                        "status": "updated",
                        "price": applied,
                        "source": provider.name,
                    }

        return {
            "status": "unavailable",
            "message": (
                "Harga belum tersedia dari sumber eksternal. Harga "
                "terakhir yang valid dipertahankan. Silakan input manual."
            ),
        }

    @staticmethod
    def _apply(destination, price, source_name):
        try:
            price = int(price)
        except (TypeError, ValueError):
            return None
        if price < 0:
            return None

        destination.ticket_type = "fixed"
        destination.ticket_price_weekday = price
        destination.ticket_price_weekend = price
        destination.price_source = source_name
        destination.price_source_type = "scraping"
        destination.price_updated_at = timezone.now()
        destination.save()
        return price
