from django.db import models

from common.models import BaseModel


class District(BaseModel):
    """
    Kecamatan
    """

    code = models.CharField(
    max_length=10,
    unique=True,
    db_index=True,
    verbose_name="District Code"
    )

    name = models.CharField(
    max_length=100,
    unique=True,
    db_index=True,
    verbose_name="District Name"
    )

    class Meta:
        db_table = "master_district"
        verbose_name = "District"
        verbose_name_plural = "Districts"
        ordering = ["name"]

    def __str__(self):
        return self.name