# Generated manually — data migration:
#   1) rename pricing_type "PAID" -> "INDEPENDENT_PRICE" (label baru)
#   2) konversi parking_cost (satu harga legacy) -> ParkingFee "Umum"
# Field legacy ``parking_cost`` / ``is_free_parking`` TIDAK dihapus (fallback).

from django.db import migrations


def rename_paid_to_independent_price(apps, schema_editor):
    Wahana = apps.get_model("gis", "Wahana")
    Wahana.objects.filter(pricing_type="PAID").update(
        pricing_type="INDEPENDENT_PRICE"
    )


def backfill_parking_fees(apps, schema_editor):
    TouristDestination = apps.get_model("gis", "TouristDestination")
    ParkingFee = apps.get_model("gis", "ParkingFee")
    for dest in TouristDestination.objects.filter(parking_cost__isnull=False):
        ParkingFee.objects.update_or_create(
            destination=dest,
            vehicle_type="Umum",
            defaults={"price": dest.parking_cost, "is_active": True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("gis", "0014_touristdestination_google_maps_query_and_more"),
    ]

    operations = [
        migrations.RunPython(
            rename_paid_to_independent_price,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            backfill_parking_fees,
            migrations.RunPython.noop,
        ),
    ]
