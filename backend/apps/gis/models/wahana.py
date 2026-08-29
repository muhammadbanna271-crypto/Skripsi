from django.core.exceptions import ValidationError
from django.db import models

from common.models import BaseModel
from apps.gis.models.tourist_destination import TouristDestination, format_idr


class Wahana(BaseModel):
    """
    Wahana / atraksi tambahan milik sebuah destinasi wisata (relational).

    Satu destinasi punya banyak wahana (Destination 1 ── N Wahana). Harga
    wahana TIDAK disimpan sebagai JSON di Destination; tiap wahana adalah
    record sendiri dengan ``destination_id`` sebagai foreign key.

    ``pricing_type`` membedakan empat kondisi harga supaya sistem & chatbot
    tidak salah menafsirkan:
      - INCLUDED_IN_HTM    : sudah termasuk tiket masuk (tanpa biaya tambahan)
      - INDEPENDENT_PRICE  : berbayar, punya harga tambahan sendiri (wajib isi)
      - INCLUDED_IN_PACKAGE: harga mengikuti tiket/bundle/package tertentu,
                             TIDAK punya harga independen
      - PRICE_UNKNOWN      : harga belum tersedia (BUKAN gratis)
    """

    INCLUDED_IN_HTM = "INCLUDED_IN_HTM"
    INDEPENDENT_PRICE = "INDEPENDENT_PRICE"
    INCLUDED_IN_PACKAGE = "INCLUDED_IN_PACKAGE"
    PRICE_UNKNOWN = "PRICE_UNKNOWN"

    PRICING_TYPE_CHOICES = [
        (INCLUDED_IN_HTM, "Termasuk HTM"),
        (INDEPENDENT_PRICE, "Berbayar (Harga Sendiri)"),
        (INCLUDED_IN_PACKAGE, "Termasuk Paket / Tiket"),
        (PRICE_UNKNOWN, "Harga Belum Tersedia"),
    ]

    destination = models.ForeignKey(
        TouristDestination,
        on_delete=models.CASCADE,
        related_name="wahanas",
        verbose_name="Destinasi",
    )

    name = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name="Nama Wahana",
    )

    pricing_type = models.CharField(
        max_length=20,
        choices=PRICING_TYPE_CHOICES,
        default=PRICE_UNKNOWN,
        verbose_name="Kategori Harga",
        help_text=(
            "'Termasuk HTM' = sudah tercakup tiket masuk; "
            "'Berbayar (Harga Sendiri)' = ada biaya tambahan; "
            "'Termasuk Paket/Tiket' = harga mengikuti bundle, tanpa harga "
            "independen; 'Harga Belum Tersedia' = datanya belum ada "
            "(bukan gratis)."
        ),
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Harga (IDR)",
        help_text="Wajib diisi hanya bila kategori = Berbayar (Harga Sendiri).",
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
        db_table = "gis_wahana"
        verbose_name = "Wahana"
        verbose_name_plural = "Wahana"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["destination", "name"],
                name="uniq_wahana_destination_name",
            ),
        ]

    def __str__(self):
        return f"{self.name} — {self.destination.name}"

    @property
    def price_int(self):
        """Harga sebagai int (untuk JSON), atau None."""
        if self.price is None:
            return None
        try:
            return int(self.price)
        except (TypeError, ValueError):
            return None

    @property
    def price_display(self):
        """Label harga sesuai kategori (UI/chatbot/Excel)."""
        if self.pricing_type == self.INCLUDED_IN_HTM:
            return "Termasuk HTM"
        if self.pricing_type == self.INCLUDED_IN_PACKAGE:
            return "Termasuk Paket / Tiket"
        if self.pricing_type == self.PRICE_UNKNOWN:
            return "Harga belum tersedia"
        if self.price is None:
            return "Belum tersedia"
        return format_idr(self.price)

    def clean(self):
        super().clean()
        if self.pricing_type == self.INCLUDED_IN_HTM and self.price is not None:
            raise ValidationError({
                "price": "Wahana yang termasuk HTM tidak boleh punya harga.",
            })
        if self.pricing_type == self.INCLUDED_IN_PACKAGE and self.price is not None:
            raise ValidationError({
                "price": (
                    "Wahana yang termasuk paket/tiket tidak punya harga "
                    "independen. Biarkan harga kosong."
                ),
            })
        if self.pricing_type == self.INDEPENDENT_PRICE:
            if self.price is None:
                raise ValidationError({
                    "price": "Wahana berbayar wajib diisi harganya.",
                })
            if self.price < 0:
                raise ValidationError({"price": "Harga tidak boleh negatif."})
        if self.pricing_type == self.PRICE_UNKNOWN and self.price is not None:
            raise ValidationError({
                "price": "Wahana dengan harga belum tersedia tidak boleh punya harga.",
            })
