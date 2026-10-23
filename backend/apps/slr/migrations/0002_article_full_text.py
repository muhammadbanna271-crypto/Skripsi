from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("slr", "0001_initial")]
    operations = [
        migrations.AddField(model_name="article", name="full_text", field=models.TextField(blank=True, default="")),
        migrations.AddField(model_name="article", name="text_error", field=models.TextField(blank=True, default="")),
        migrations.AddField(model_name="article", name="text_status", field=models.CharField(db_index=True, default="not_requested", max_length=30)),
    ]
