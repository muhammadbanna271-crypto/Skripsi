# Generated manually — hapus field JSON legacy ``ride_prices`` dan
# ``bundle_prices`` setelah datanya dipindahkan ke model relational
# (Wahana & TicketBundle) di migration 0012.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("gis", "0012_wahana_ticketbundle"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="touristdestination",
            name="ride_prices",
        ),
        migrations.RemoveField(
            model_name="touristdestination",
            name="bundle_prices",
        ),
    ]
