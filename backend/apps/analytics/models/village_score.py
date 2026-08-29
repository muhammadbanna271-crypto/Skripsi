from django.db import models

from common.models import BaseModel
from apps.master.models import Village


class VillageScore(BaseModel):

    village = models.OneToOneField(
        Village,
        on_delete=models.CASCADE,
        related_name="village_score",
    )

    total_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    normalized_score = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
    )

    rank = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            "rank",
        ]

    def __str__(self):

        return self.village.name