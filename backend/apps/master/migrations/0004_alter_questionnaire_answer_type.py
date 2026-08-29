from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("master", "0003_indicator_criterion_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="questionnaire",
            name="answer_type",
            field=models.CharField(
                choices=[
                    ("boolean", "Yes / No"),
                    ("likert", "Likert Scale (1-5)"),
                    ("integer", "Integer"),
                    ("decimal", "Decimal"),
                    ("text", "Text"),
                    ("choice", "Multiple Choice"),
                ],
                default="boolean",
                max_length=20,
                verbose_name="Answer Type",
            ),
        ),
    ]