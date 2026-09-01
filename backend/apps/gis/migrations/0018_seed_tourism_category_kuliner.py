from django.db import migrations

# Tambah kategori "Kuliner" (tempat makan) supaya kategori wisata punya
# pilihan untuk restaurant/cafe. Idempotent, tidak menghapus data existing.
KULINER = "Kuliner"


def seed_tourism_category(apps, schema_editor):
    TourismCategory = apps.get_model("gis", "TourismCategory")
    TourismCategory.objects.get_or_create(
        name=KULINER,
        defaults={
            "description": "Tempat makan, cafe, dan kuliner khas Kota Batu.",
            "is_active": True,
        },
    )


def unseed_tourism_category(apps, schema_editor):
    TourismCategory = apps.get_model("gis", "TourismCategory")
    TourismCategory.objects.filter(name=KULINER).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("gis", "0017_seed_cuisine_types"),
    ]

    operations = [
        migrations.RunPython(
            seed_tourism_category,
            reverse_code=unseed_tourism_category,
        ),
    ]
