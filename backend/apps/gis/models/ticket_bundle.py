from django.db import models

from common.models import BaseModel
from apps.gis.models.tourist_destination import TouristDestination, format_idr
from apps.gis.models.wahana import Wahana


class TicketBundle(BaseModel):
    """
    Tiket bundle / paket gabungan milik sebuah destinasi wisata.

    Relasi:
      - Destination 1 ── N TicketBundle
      - TicketBundle N ── M Wahana (ManyToMany)

    Satu bundle berisi beberapa wahana; satu wahana boleh masuk beberapa
    bundle sekaligus. Harga bundle adalah harga sendiri (BUKAN penjumlahan
    harga wahana di dalamnya). ``includes_entry_ticket`` menandai apakah
    HTM/tiket masuk termasuk dalam paket.
    """

    destination = models.ForeignKey(
        TouristDestination,
        on_delete=models.CASCADE,
        related_name="bundles",
        verbose_name="Destinasi",
    )

    name = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name="Nama Bundle",
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Harga Bundle (IDR)",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Deskripsi",
    )

    includes_entry_ticket = models.BooleanField(
        default=False,
        verbose_name="Termasuk HTM",
        help_text="Centang bila tiket masuk (HTM) sudah tercakup dalam paket.",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif",
    )

    wahanas = models.ManyToManyField(
        Wahana,
        related_name="bundles",
        blank=True,
        verbose_name="Wahana",
        help_text="Wahana yang termasuk dalam bundle ini.",
    )

    class Meta:
        db_table = "gis_ticket_bundle"
        verbose_name = "Tiket Bundle"
        verbose_name_plural = "Tiket Bundle"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["destination", "name"],
                name="uniq_bundle_destination_name",
            ),
        ]

    def __str__(self):
        return f"{self.name} — {self.destination.name}"

    @property
    def price_int(self):
        if self.price is None:
            return None
        try:
            return int(self.price)
        except (TypeError, ValueError):
            return None

    @property
    def price_display(self):
        if self.price is None:
            return "Belum tersedia"
        return format_idr(self.price)

    @property
    def rides_display(self):
        """Nama wahana yang termasuk (teks gabungan), atau None."""
        names = [w.name for w in self.wahanas.all()]
        return ", ".join(names) if names else None
