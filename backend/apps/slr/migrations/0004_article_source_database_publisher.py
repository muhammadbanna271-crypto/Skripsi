from django.db import migrations, models


def backfill_source_database(apps, schema_editor):
    Article = apps.get_model("slr", "Article")
    ArticleSource = apps.get_model("slr", "ArticleSource")

    for article in Article.objects.all().iterator():
        providers = set(
            ArticleSource.objects.filter(article_id=article.pk).values_list(
                "provider", flat=True
            )
        )
        if {"semantic_scholar", "crossref"}.issubset(providers):
            article.source_database = "both"
        elif "semantic_scholar" in providers:
            article.source_database = "semantic_scholar"
        elif "crossref" in providers:
            article.source_database = "crossref"
        article.save(update_fields=["source_database"])


class Migration(migrations.Migration):
    dependencies = [("slr", "0003_keyword")]

    operations = [
        migrations.AddField(
            model_name="article",
            name="publisher",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="article",
            name="source_database",
            field=models.CharField(blank=True, db_index=True, default="", max_length=50),
        ),
        migrations.RunPython(backfill_source_database, migrations.RunPython.noop),
    ]
