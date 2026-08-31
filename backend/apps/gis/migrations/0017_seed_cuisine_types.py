from django.db import migrations

# Nilai awal "Cita Rasa" & "Jenis Masakan" supaya field cuisine_types
# pada form destinasi/restaurant langsung punya pilihan (tanpa harus
# diisi manual lewat admin). Idempotent (get_or_create), tidak mengubah
# data yang sudah ada.
FLAVORS = ["Gurih", "Manis", "Pedas", "Asin", "Asam", "Segar"]
CUISINES = ["Tradisional", "Modern", "Nusantara", "Western", "Asian"]


def seed_cuisine_types(apps, schema_editor):
    CuisineType = apps.get_model("gis", "CuisineType")
    for name in FLAVORS:
        CuisineType.objects.get_or_create(name=name, kind="flavor")
    for name in CUISINES:
        CuisineType.objects.get_or_create(name=name, kind="cuisine")


def unseed_cuisine_types(apps, schema_editor):
    CuisineType = apps.get_model("gis", "CuisineType")
    CuisineType.objects.filter(
        name__in=FLAVORS + CUISINES,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("gis", "0016_cuisinetype_touristdestination_ambiance_and_more"),
    ]

    operations = [
        migrations.RunPython(
            seed_cuisine_types,
            reverse_code=unseed_cuisine_types,
        ),
    ]
