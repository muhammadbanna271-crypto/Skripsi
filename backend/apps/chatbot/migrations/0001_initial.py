from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ChatbotUsage",
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
                    "month",
                    models.CharField(
                        max_length=7,
                        unique=True,
                    ),
                ),
                (
                    "message_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "estimated_cost_usd",
                    models.DecimalField(
                        decimal_places=4,
                        default=0,
                        max_digits=8,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
            ],
        ),
    ]
