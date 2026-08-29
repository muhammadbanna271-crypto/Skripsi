"""
Import koordinat TITIK PUSAT desa ke Village.latitude/longitude.

21 desa diambil dari OpenStreetMap (node ``place=village`` / ``place=town``)
via Overpass API pada 2026-08-25. 3 desa tidak punya node place di OSM,
sehingga diambil dari sumber terbuka lain (Mapcarta / kantor kelurahan):
    Ngaglik, Sisir, Sumberbrantas

Semua ini adalah koordinat titik pusat (centroid / kantor desa),
BUKAN batas poligon.

Sumber: OpenStreetMap (ODbL) + Mapcarta.
Jalankan: python manage.py import_village_coordinates
"""

from django.core.management.base import BaseCommand

from apps.master.models import Village


# name -> (latitude, longitude)
COORDINATES = {
    "Oro-oro Ombo": (-7.8940468, 112.5291987),
    "Pesanggrahan": (-7.8728609, 112.5140459),
    "Songgokerto": (-7.8662832, 112.5074324),
    "Sumberejo": (-7.8596262, 112.5104450),
    "Temas": (-7.8774458, 112.5375263),
    "Sidomulyo": (-7.8484143, 112.5223668),
    "Bumiaji": (-7.8403491, 112.5278775),
    "Punten": (-7.8377039, 112.5285065),
    "Tulungrejo": (-7.8259450, 112.5300465),
    "Sumbergondo": (-7.8318775, 112.5304437),
    "Bulukerto": (-7.8472922, 112.5324328),
    "Gunungsari": (-7.8422898, 112.5158942),
    "Pandanrejo": (-7.8641018, 112.5389698),
    "Giripurno": (-7.8653300, 112.5599907),
    "Beji": (-7.8922746, 112.5482137),
    "Torongrejo": (-7.8879576, 112.5591620),
    "Mojorejo": (-7.9003627, 112.5584729),
    "Pendem": (-7.9019644, 112.5810758),
    "Junrejo": (-7.9081602, 112.5517791),
    "Dadaprejo": (-7.9120572, 112.5788428),
    "Tlekung": (-7.9108851, 112.5311895),
    # 3 desa berikut dari Mapcarta / kantor kelurahan (tanpa node OSM):
    "Ngaglik": (-7.877628, 112.5170594),
    "Sisir": (-7.8698241, 112.5276464),
    "Sumberbrantas": (-7.7653486, 112.5290429),
}


class Command(BaseCommand):
    help = (
        "Isi Village.latitude/longitude dari koordinat titik pusat OSM "
        "(hanya desa yang ditemukan)."
    )

    def handle(self, *args, **options):
        updated = 0
        missing = []

        for name, (lat, lon) in COORDINATES.items():
            count = Village.objects.filter(name=name).update(
                latitude=lat,
                longitude=lon,
            )
            if count:
                updated += count
            else:
                missing.append(name)

        self.stdout.write(
            self.style.SUCCESS(
                f"Koordinat terisi untuk {updated} desa."
            )
        )

        all_names = list(Village.objects.values_list("name", flat=True))
        not_in_osm = [
            n for n in all_names if n not in COORDINATES
        ]
        if not_in_osm:
            self.stdout.write(
                self.style.WARNING(
                    "Desa tanpa koordinat (tidak ada di OSM): "
                    + ", ".join(sorted(not_in_osm))
                )
            )

        if missing:
            self.stdout.write(
                self.style.WARNING(
                    "Nama tidak cocok dengan database: "
                    + ", ".join(missing)
                )
            )
