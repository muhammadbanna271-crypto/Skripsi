"""
Import destinasi wisata Kota Batu dari OpenStreetMap (Overpass API).

Jalankan: python manage.py import_tourist_destinations

Sumber: OpenStreetMap (ODbL). Hari tutup digali dari tag ``opening_hours``.
Harga tiket sengaja tidak diisi (tag harga OSM jarang tersedia & formatnya
tidak konsisten) — biarkan null supaya trip planner menyatakan "belum
tersedia", bukan mengarang angka.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.gis.models import TourismCategory, TouristDestination
from apps.gis.services import osm_import
from apps.master.models import Village


class Command(BaseCommand):
    help = (
        "Import destinasi wisata Kota Batu dari OpenStreetMap (Overpass)."
    )

    def handle(self, *args, **options):
        bbox = self._compute_bbox()
        self.stdout.write("Mengambil data dari Overpass...")

        elements = osm_import.fetch_osm_destinations(bbox)
        self.stdout.write(f"  {len(elements)} elemen mentah.")

        elements = osm_import.dedupe_by_name(elements)
        self.stdout.write(f"  {len(elements)} nama unik setelah dedupe.")

        created = 0
        updated = 0
        skipped = 0

        for element in elements:
            tags = element.get("tags") or {}
            name = (tags.get("name") or "").strip()
            if not name:
                skipped += 1
                continue

            lat, lon = osm_import.element_coords(element)
            if lat is None or lon is None:
                skipped += 1
                continue

            village, _km = osm_import.nearest_village(lat, lon)

            tourism_type, category_names = osm_import.map_tourism_type(tags)
            closed_days, open_min, close_min = osm_import.parse_opening_hours(
                tags.get("opening_hours")
            )

            description = (
                tags.get("description")
                or tags.get("description:en")
                or ""
            )

            obj, was_created = self._get_or_create(name)

            obj.village = village
            obj.latitude = lat
            obj.longitude = lon
            obj.tourism_type = tourism_type or ""
            obj.description = description
            obj.opening_time = osm_import.minutes_to_time(open_min)
            obj.closing_time = osm_import.minutes_to_time(close_min)
            obj.closed_days = closed_days
            obj.source = "OpenStreetMap (Overpass)"
            obj.is_active = True
            obj.save()

            if category_names:
                categories = [
                    TourismCategory.objects.get_or_create(name=c)[0]
                    for c in category_names
                ]
                obj.categories.set(categories)
            else:
                obj.categories.clear()

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Selesai: {created} baru, {updated} diperbarui, "
                f"{skipped} dilewati."
            )
        )

    def _compute_bbox(self):
        coords = list(
            Village.objects.filter(
                latitude__isnull=False,
                longitude__isnull=False,
            ).values_list("latitude", "longitude")
        )
        if not coords:
            raise CommandError(
                "Belum ada koordinat desa. Jalankan "
                "import_village_coordinates dulu."
            )

        lats = [float(c[0]) for c in coords]
        lons = [float(c[1]) for c in coords]
        pad = 0.03
        return (
            min(lats) - pad,
            min(lons) - pad,
            max(lats) + pad,
            max(lons) + pad,
        )

    @staticmethod
    def _get_or_create(name):
        obj = TouristDestination.objects.filter(name__iexact=name).first()
        if obj is not None:
            return obj, False
        return TouristDestination(name=name), True
