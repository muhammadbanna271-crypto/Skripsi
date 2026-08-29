from django.db import models

from common.models import BaseModel

from apps.master.models import Village

from .survey import Survey


class SurveyVillage(BaseModel):
    """
    Village assigned to survey
    """

    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name="survey_villages",
    )

    village = models.ForeignKey(
        Village,
        on_delete=models.PROTECT,
        related_name="survey_villages",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:

        db_table = "survey_village"

        verbose_name = "Survey Village"

        verbose_name_plural = "Survey Villages"

        unique_together = (
            "survey",
            "village",
        )

    def __str__(self):

        return f"{self.survey} - {self.village}"