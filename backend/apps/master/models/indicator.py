from django.db import models

from common.models import BaseModel
from .variable import Variable


class Indicator(BaseModel):
    """
    Master Indicator
    """

    variable = models.ForeignKey(
        Variable,
        on_delete=models.PROTECT,
        related_name="indicators",
        verbose_name="Variable"
    )

    code = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name="Indicator Code"
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Indicator Name"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description"
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        verbose_name="Weight"
    )

    # ============================
    # TAMBAHKAN BAGIAN INI
    # ============================

    CRITERION_CHOICES = [
        ("benefit", "Benefit"),
        ("cost", "Cost"),
    ]

    criterion_type = models.CharField(
        max_length=10,
        choices=CRITERION_CHOICES,
        default="benefit",
        verbose_name="Criterion Type",
    )

    # ============================

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "master_indicator"
        verbose_name = "Indicator"
        verbose_name_plural = "Indicators"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"