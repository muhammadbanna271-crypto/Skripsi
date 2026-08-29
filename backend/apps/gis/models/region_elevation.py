from django.db import models

from common.models import BaseModel
from apps.master.models import Village


class RegionElevation(BaseModel):
    """
    Statistik elevasi per desa (hasil agregasi DEM/raster lewat zonal
    statistics). Semua field nullable — data hanya diisi kalau dataset
    elevasi resmi benar-benar tersedia. TIDAK ada nilai palsu.
    """

    village = models.OneToOneField(
        Village,
        on_delete=models.CASCADE,
        related_name="elevation",
        verbose_name="Village",
    )

    min_elevation = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Minimum Elevation (m)",
    )

    max_elevation = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Maximum Elevation (m)",
    )

    mean_elevation = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Mean Elevation (m)",
    )

    median_elevation = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Median Elevation (m)",
    )

    std_deviation = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Standard Deviation (m)",
    )

    source_dataset = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Source Dataset",
        help_text="Contoh: DEMNAS 8m, SRTM 30m, dsb.",
    )

    resolution = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Resolution",
        help_text="Contoh: 8m, 30m, 90m.",
    )

    class Meta:
        db_table = "gis_region_elevation"
        verbose_name = "Region Elevation"
        verbose_name_plural = "Region Elevations"

    def __str__(self):
        return f"{self.village.name} — elevasi"

    @property
    def range_meters(self):
        if self.min_elevation is None or self.max_elevation is None:
            return None
        return round(self.max_elevation - self.min_elevation, 1)
