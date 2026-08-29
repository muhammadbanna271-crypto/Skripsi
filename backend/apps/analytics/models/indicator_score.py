from django.db import models

from common.models import BaseModel
from apps.master.models import Indicator
from apps.master.models import Village


class IndicatorScore(BaseModel):

    village = models.ForeignKey(
        Village,
        on_delete=models.CASCADE,
        related_name="indicator_scores",
    )

    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.CASCADE,
        related_name="scores",
    )

    score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    class Meta:
        ordering = [
            "indicator",
        ]

    def __str__(self):

        return f"{self.village.name} - {self.indicator.name}"