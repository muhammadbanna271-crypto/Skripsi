from django.db import models

from common.models import BaseModel
from apps.master.models import Variable
from apps.master.models import Village


class VariableScore(BaseModel):

    village = models.ForeignKey(
        Village,
        on_delete=models.CASCADE,
        related_name="variable_scores",
    )

    variable = models.ForeignKey(
        Variable,
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
            "variable",
        ]

    def __str__(self):

        return f"{self.village.name} - {self.variable.name}"