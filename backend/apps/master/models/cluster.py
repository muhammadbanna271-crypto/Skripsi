from django.db import models

from common.models import BaseModel


class Cluster(BaseModel):
    """
    Hasil pengelompokan desa.
    """

    code = models.CharField(
    max_length=10,
    unique=True,
    db_index=True,
    verbose_name="Cluster Code"
    )

    name = models.CharField(
    max_length=100,
    unique=True,
    db_index=True,
    verbose_name="Cluster Name"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description"
    )

    color = models.CharField(
        max_length=20,
        default="#0d6efd",
        verbose_name="Color"
    )

    class Meta:
        db_table = "master_cluster"
        verbose_name = "Cluster"
        verbose_name_plural = "Clusters"
        ordering = ["code"]

    def __str__(self):
        return self.name