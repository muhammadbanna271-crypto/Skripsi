from django.db import models

from common.models import BaseModel


class Survey(BaseModel):
    """
    Survey Session
    """

    name = models.CharField(
        max_length=200,
        verbose_name="Survey Name",
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description",
    )

    start_date = models.DateField(
        verbose_name="Start Date",
    )

    end_date = models.DateField(
        verbose_name="End Date",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:

        db_table = "survey"

        verbose_name = "Survey"

        verbose_name_plural = "Surveys"

        ordering = [
            "-start_date",
        ]

    def __str__(self):

        return self.name