from django.db import models

from common.models import BaseModel

from apps.respondent.models import Respondent
from apps.master.models import Questionnaire


class Response(BaseModel):
    """
    Survey Response
    """

    respondent = models.ForeignKey(
        Respondent,
        on_delete=models.CASCADE,
        related_name="responses",
    )

    questionnaire = models.ForeignKey(
        Questionnaire,
        on_delete=models.CASCADE,
        related_name="responses",
    )

    answer_boolean = models.BooleanField(
        null=True,
        blank=True,
    )

    answer_integer = models.IntegerField(
        null=True,
        blank=True,
    )

    answer_decimal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    answer_text = models.TextField(
        blank=True,
    )

    score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    class Meta:

        db_table = "survey_response"

        ordering = [
            "respondent",
        ]

    def __str__(self):

        return f"{self.respondent} - {self.questionnaire}"