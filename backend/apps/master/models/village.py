from django.db import models

from common.models import BaseModel
from .district import District
from .cluster import Cluster


class Village(BaseModel):
    """
    Village Master Data
    """

    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name="villages",
        verbose_name="District"
    )

    cluster = models.ForeignKey(
        Cluster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="villages",
        verbose_name="Cluster"
    )

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

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
        help_text="Deskripsi singkat karakteristik & keunikan desa.",
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "master_village"
        verbose_name = "Village"
        verbose_name_plural = "Villages"
        ordering = ["name"]

    def __str__(self):
        return self.name