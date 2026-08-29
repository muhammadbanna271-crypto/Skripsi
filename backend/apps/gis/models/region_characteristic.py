from django.db import models

from common.models import BaseModel
from apps.master.models import Village


class RegionCharacteristic(BaseModel):
    """
    Karakteristik / keunikan sebuah wilayah (desa/kelurahan).

    Disimpan sebagai data fleksibel (key-value ber-tipe), BUKAN kolom
    hard-code, supaya admin bisa menambah jenis karakteristik baru
    (komoditas, perkebunan, sumber daya alam, budaya, fasilitas, dll.)
    tanpa mengubah kode frontend setiap kali ada atribut baru.
    """

    VALUE_TEXT = "text"
    VALUE_NUMBER = "number"
    VALUE_BOOLEAN = "boolean"

    VALUE_TYPE_CHOICES = [
        (VALUE_TEXT, "Text"),
        (VALUE_NUMBER, "Number"),
        (VALUE_BOOLEAN, "Boolean"),
    ]

    village = models.ForeignKey(
        Village,
        on_delete=models.CASCADE,
        related_name="characteristics",
        verbose_name="Village",
    )

    characteristic_type = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="Characteristic Type",
        help_text=(
            "Kategori, contoh: geography, economy, culture, "
            "tourism_potential, facility, accessibility, commodity."
        ),
    )

    characteristic_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Characteristic Name",
        help_text="Contoh: ketinggian, luas wilayah, komoditas, potensi wisata.",
    )

    value = models.TextField(
        verbose_name="Value",
        help_text="Nilai karakteristik (teks bebas).",
    )

    value_type = models.CharField(
        max_length=20,
        choices=VALUE_TYPE_CHOICES,
        default=VALUE_TEXT,
        verbose_name="Value Type",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
    )

    source = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Source",
    )

    class Meta:
        db_table = "gis_region_characteristic"
        verbose_name = "Region Characteristic"
        verbose_name_plural = "Region Characteristics"
        ordering = ["characteristic_type", "characteristic_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["village", "characteristic_type", "characteristic_name"],
                name="uniq_region_characteristic",
            ),
        ]

    def __str__(self):
        return f"{self.village.name} — {self.characteristic_name}"

    @property
    def numeric_value(self):
        """Parse value menjadi float jika value_type = number, else None."""
        if self.value_type != self.VALUE_NUMBER:
            return None
        try:
            return float(self.value)
        except (TypeError, ValueError):
            return None
