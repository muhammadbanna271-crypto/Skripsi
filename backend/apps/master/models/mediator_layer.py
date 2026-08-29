from django.db import models

from common.models import BaseModel


class MediatorLayer(BaseModel):
    """
    Layer mediator (0..N). Layer bisa dibuat/dihapus/dinonaktifkan/
    diaktifkan kembali secara independen dari variable di dalamnya.

    Mediator variable menunjuk ke layer ini lewat
    ``Variable.mediator_layer``. Layer yang ``is_active=False``
    otomatis di-exclude dari analysis (Predictor -> Response).
    """

    number = models.PositiveIntegerField(
        unique=True,
        verbose_name="Layer Number",
    )

    name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Layer Name",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
    )

    class Meta:
        db_table = "master_mediator_layer"
        verbose_name = "Mediator Layer"
        verbose_name_plural = "Mediator Layers"
        ordering = ["number"]

    def __str__(self):
        if self.name:
            return f"Layer {self.number} — {self.name}"
        return f"Layer {self.number}"
