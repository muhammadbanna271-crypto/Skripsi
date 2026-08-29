"""
Import elevasi & suhu destinasi dari file CSV.

Sumber data (TIDAK dikarang — data harus disediakan lewat CSV):
- Elevasi : hasil ekstraksi DEM pada koordinat destinasi.
  Sumber publik yang sesuai: DEMNAS (BIG), ALOS/PALSAR (JAXA), SRTM.
- Suhu    : dataset publik, mis. WorldClim (rata-rata bulanan) atau BMKG.

Format CSV (header wajib):
    name,elevation_meters,elevation_source,temperature_c,temperature_source,temperature_date

Contoh:
    name,elevation_meters,elevation_source,temperature_c,temperature_source,temperature_date
    Alun-Alun Kota Batu,900,DEMNAS,19.5,WorldClim,2026-01-01

Jalankan:
    python manage.py import_destination_climate path/to/file.csv
"""

import csv
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.gis.models import TouristDestination


class Command(BaseCommand):
    help = "Import elevasi & suhu destinasi dari file CSV."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path file CSV.")

    def handle(self, *args, **options):
        path = options["csv_path"]
        updated = 0
        skipped = 0
        missing = 0

        try:
            with open(path, newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    name = (row.get("name") or "").strip()
                    if not name:
                        skipped += 1
                        continue

                    dest = TouristDestination.objects.filter(
                        name__iexact=name
                    ).first()
                    if dest is None:
                        missing += 1
                        continue

                    dest.elevation_meters = self._float(
                        row.get("elevation_meters")
                    )
                    dest.elevation_source = (
                        row.get("elevation_source") or ""
                    ).strip()
                    dest.temperature_c = self._float(
                        row.get("temperature_c")
                    )
                    dest.temperature_source = (
                        row.get("temperature_source") or ""
                    ).strip()
                    dest.temperature_date = self._date(
                        row.get("temperature_date")
                    )
                    dest.save()
                    updated += 1
        except OSError as exc:
            raise CommandError(f"Gagal membaca file: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Selesai: {updated} diperbarui, {skipped} dilewati "
                f"(nama kosong), {missing} tidak ditemukan."
            )
        )

    @staticmethod
    def _float(value):
        value = (value or "").strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def _date(value):
        value = (value or "").strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
