import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("slr", "0002_article_full_text")]
    operations = [
        migrations.CreateModel(
            name="Keyword",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
                ("original_name", models.CharField(max_length=500)),
                ("normalized_name", models.CharField(db_index=True, max_length=500)),
                ("article", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="slr_keywords", to="slr.article")),
                ("evidence", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="keywords", to="slr.evidence")),
                ("extraction", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="keywords", to="slr.extraction")),
            ],
        ),
    ]
