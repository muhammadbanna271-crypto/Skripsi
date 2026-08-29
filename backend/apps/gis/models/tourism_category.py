from django.db import models

from common.models import BaseModel


class TourismCategory(BaseModel):
    """
    Kategori wisata fleksibel (wisata alam, air terjun, perkebunan,
    budaya, edukasi, kuliner, keluarga, petualangan, religi, dll.).

    Disimpan sebagai data (bukan hard-code di chatbot) supaya admin
    bisa menambah kategori baru kapan saja.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Category Name",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
    )

    class Meta:
        db_table = "gis_tourism_category"
        verbose_name = "Tourism Category"
        verbose_name_plural = "Tourism Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name
