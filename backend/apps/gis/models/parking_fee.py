from django.db import models

from common.models import BaseModel
from apps.gis.models.tourist_destination import TouristDestination, format_idr


class ParkingFee(BaseModel):
    """
    Biaya parkir per jenis kendaraan milik sebuah destinasi wisata.

    Satu destinasi bisa punya banyak jenis kendaraan dengan tarif berbeda
    (mis. Motor Rp5.000, Mobil Rp10.000, Bus Rp20.000). Model ini menggantikan
    konsep "satu harga parkir untuk semua kendaraan"; field legacy
    ``TouristDestination.parking_cost`` tetap dipertahankan sebagai fallback
    bila belum ada data per kendaraan.
    """

    destination = models.ForeignKey(
        TouristDestination,
        on_delete=models.CASCADE,
        related_name="parking_fees",
        verbose_name="Destinasi",
    )

    vehicle_type = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="Jenis Kendaraan",
        help_text="Contoh: Motor, Mobil, Bus, Pickup, dsb.",
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Biaya Parkir (IDR)",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Catatan",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif",
    )

    class Meta:
        db_table = "gis_parking_fee"
        verbose_name = "Biaya Parkir"
        verbose_name_plural = "Biaya Parkir"
        ordering = ["vehicle_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["destination", "vehicle_type"],
                name="uniq_parking_destination_vehicle",
            ),
        ]

    def __str__(self):
        return f"{self.vehicle_type} — {self.destination.name}"

    @property
    def price_int(self):
        try:
            return int(self.price)
        except (TypeError, ValueError):
            return None

    @property
    def price_display(self):
        return format_idr(self.price)
