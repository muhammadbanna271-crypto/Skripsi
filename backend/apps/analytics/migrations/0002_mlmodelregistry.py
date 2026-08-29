from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MLModelRegistry",
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
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Created At",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Updated At",
                    ),
                ),
                (
                    "n_clusters",
                    models.PositiveIntegerField(default=3),
                ),
                (
                    "n_samples",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "silhouette_score",
                    models.FloatField(blank=True, null=True),
                ),
                (
                    "inertia",
                    models.FloatField(blank=True, null=True),
                ),
                (
                    "cluster_mapping",
                    models.JSONField(blank=True, default=dict),
                ),
                (
                    "feature_importance",
                    models.JSONField(blank=True, default=list),
                ),
                (
                    "variable_importance",
                    models.JSONField(blank=True, default=list),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
