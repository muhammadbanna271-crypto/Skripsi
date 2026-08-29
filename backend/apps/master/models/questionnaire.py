from django.db import models

from common.models import BaseModel
from .indicator import Indicator


class Questionnaire(BaseModel):
    """
    Master Questionnaire
    """

    ANSWER_TYPES = [
        ("boolean", "Yes / No"),
        ("likert", "Likert Scale (1-5)"),
        ("integer", "Integer"),
        ("decimal", "Decimal"),
        ("text", "Text"),
        ("choice", "Multiple Choice"),
    ]

    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.CASCADE,
        related_name="questionnaires",
        verbose_name="Indicator"
    )

    question = models.TextField(
        verbose_name="Question"
    )

    answer_type = models.CharField(
        max_length=20,
        choices=ANSWER_TYPES,
        default="boolean",
        verbose_name="Answer Type"
    )

    question_order = models.PositiveIntegerField(
        default=1,
        verbose_name="Question Order"
    )

    is_required = models.BooleanField(
        default=True,
        verbose_name="Required"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )

    class Meta:
        db_table = "master_questionnaire"
        verbose_name = "Questionnaire"
        verbose_name_plural = "Questionnaires"
        ordering = [
            "indicator",
            "question_order",
        ]

    def __str__(self):
        return f"{self.indicator.code} - Q{self.question_order}"