# Generated manually — buat model relational Wahana & TicketBundle,
# lalu migrasikan data JSON lama (ride_prices/bundle_prices) ke model baru.

import django.db.models.deletion
from decimal import Decimal, InvalidOperation

from django.db import migrations, models


def migrate_legacy_prices(apps, schema_editor):
    """
    Konversi data lama:
      - ``TouristDestination.ride_prices`` (JSON) -> model ``Wahana``
      - ``TouristDestination.bundle_prices`` (JSON) -> model ``TicketBundle``
        + relasi M2M ke ``Wahana`` (dipetakan lewat nama wahana).

    Data yang gagal diparse (bukan dict / nama kosong) DILEWATI, tidak
    dihapus — field JSON lama masih dipertahankan sampai migration berikutnya
    menghapusnya, dan jumlah item yang dilewati dicetak sebagai laporan.
    """
    TouristDestination = apps.get_model("gis", "TouristDestination")
    Wahana = apps.get_model("gis", "Wahana")
    TicketBundle = apps.get_model("gis", "TicketBundle")

    total_wahana = 0
    total_bundle = 0
    skipped_rides = 0
    skipped_bundles = 0

    for dest in TouristDestination.objects.all():
        # --- ride_prices -> Wahana ---
        name_to_wahana = {}
        for item in (dest.ride_prices or []):
            if not isinstance(item, dict):
                skipped_rides += 1
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                skipped_rides += 1
                continue

            price_raw = item.get("price")
            price = None
            pricing_type = "PRICE_UNKNOWN"
            if price_raw is not None:
                try:
                    price = Decimal(str(price_raw))
                    pricing_type = "PAID"
                except (InvalidOperation, ValueError, TypeError):
                    price = None
                    pricing_type = "PRICE_UNKNOWN"

            wahana, created = Wahana.objects.update_or_create(
                destination=dest,
                name=name,
                defaults={
                    "pricing_type": pricing_type,
                    "price": price,
                    "is_active": True,
                },
            )
            if created:
                total_wahana += 1
            name_to_wahana[name.lower()] = wahana

        # --- bundle_prices -> TicketBundle + M2M ---
        for item in (dest.bundle_prices or []):
            if not isinstance(item, dict):
                skipped_bundles += 1
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                skipped_bundles += 1
                continue

            price_raw = item.get("price")
            price = None
            if price_raw is not None:
                try:
                    price = Decimal(str(price_raw))
                except (InvalidOperation, ValueError, TypeError):
                    price = None

            bundle = TicketBundle.objects.create(
                destination=dest,
                name=name,
                price=price,
                includes_entry_ticket=bool(item.get("includes_htm")),
                is_active=True,
            )
            total_bundle += 1

            for ride_name in (item.get("rides") or []):
                wahana = name_to_wahana.get(str(ride_name).strip().lower())
                if wahana is not None:
                    bundle.wahanas.add(wahana)

    print(
        "[gis] Migrasi harga: %d wahana, %d bundle dibuat. "
        "Dilewati: %d wahana, %d bundle (format JSON tidak valid)."
        % (total_wahana, total_bundle, skipped_rides, skipped_bundles)
    )


class Migration(migrations.Migration):

    dependencies = [
        ("gis", "0011_touristdestination_elevation_meters_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Wahana",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "name",
                    models.CharField(
                        db_index=True, max_length=150, verbose_name="Nama Wahana"
                    ),
                ),
                (
                    "pricing_type",
                    models.CharField(
                        choices=[
                            ("INCLUDED_IN_HTM", "Gratis / Termasuk HTM"),
                            ("PAID", "Berbayar"),
                            ("PRICE_UNKNOWN", "Harga Belum Tersedia"),
                        ],
                        default="PRICE_UNKNOWN",
                        help_text="'Gratis/Termasuk HTM' = sudah tercakup tiket masuk; 'Berbayar' = ada biaya tambahan; 'Harga Belum Tersedia' = datanya belum ada (bukan gratis).",
                        max_length=20,
                        verbose_name="Kategori Harga",
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Wajib diisi hanya bila kategori = Berbayar.",
                        max_digits=12,
                        null=True,
                        verbose_name="Harga (IDR)",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, default="", verbose_name="Deskripsi"
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Aktif")),
                (
                    "destination",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wahanas",
                        to="gis.touristdestination",
                        verbose_name="Destinasi",
                    ),
                ),
            ],
            options={
                "verbose_name": "Wahana",
                "verbose_name_plural": "Wahana",
                "db_table": "gis_wahana",
                "ordering": ["name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("destination", "name"),
                        name="uniq_wahana_destination_name",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="TicketBundle",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "name",
                    models.CharField(
                        db_index=True, max_length=150, verbose_name="Nama Bundle"
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                        verbose_name="Harga Bundle (IDR)",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, default="", verbose_name="Deskripsi"
                    ),
                ),
                (
                    "includes_entry_ticket",
                    models.BooleanField(
                        default=False,
                        help_text="Centang bila tiket masuk (HTM) sudah tercakup dalam paket.",
                        verbose_name="Termasuk HTM",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Aktif")),
                (
                    "destination",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bundles",
                        to="gis.touristdestination",
                        verbose_name="Destinasi",
                    ),
                ),
                (
                    "wahanas",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Wahana yang termasuk dalam bundle ini.",
                        related_name="bundles",
                        to="gis.wahana",
                        verbose_name="Wahana",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tiket Bundle",
                "verbose_name_plural": "Tiket Bundle",
                "db_table": "gis_ticket_bundle",
                "ordering": ["name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("destination", "name"),
                        name="uniq_bundle_destination_name",
                    )
                ],
            },
        ),
        migrations.RunPython(migrate_legacy_prices, migrations.RunPython.noop),
    ]
