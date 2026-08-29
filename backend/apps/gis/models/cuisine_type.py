from django.db import models

from common.models import BaseModel


class CuisineType(BaseModel):
    """
    Cita rasa / jenis makanan untuk restaurant (dipakai chatbot & itinerary
    supaya bisa rekomendasi "makanan pedas", "masakan Nusantara", dst.).

    ``kind`` membedakan dua dimensi:
      - flavor  : cita rasa (manis, pedas, gurih, asin, segar)
      - cuisine : jenis masakan (Nusantara, Western, Asian, tradisional, modern)
    """

    KIND_CHOICES = [
        ("flavor", "Cita Rasa"),
        ("cuisine", "Jenis Masakan"),
    ]

    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Nama",
    )

    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default="flavor",
        verbose_name="Jenis",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Deskripsi",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif",
    )

    class Meta:
        db_table = "gis_cuisine_type"
        verbose_name = "Cita Rasa / Jenis Masakan"
        verbose_name_plural = "Cita Rasa / Jenis Masakan"
        ordering = ["kind", "name"]

    def __str__(self):
        return self.name
