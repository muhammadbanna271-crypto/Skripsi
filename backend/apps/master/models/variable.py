import uuid

from django.db import models

from common.models import BaseModel
from .mediator_layer import MediatorLayer


class Variable(BaseModel):
    """
    Master Variable — dynamic variable modeling.

    Setiap variable punya role: Predictor / Mediator / Response.
    ``code`` (X1/Y1/Z1) adalah DISPLAY/ANALYSIS code yang di-generate
    otomatis dari role + urutan, BUKAN primary key (primary key = ``id``).
    Urutan variable persistis lewat ``order`` (dan ``mediator_layer``
    untuk mediator), sehingga reorder/move tidak mengubah ``id``.

    Mapping role -> prefix code:

        predictor -> X1, X2, ..., Xn
        mediator  -> Y1, Y2, ..., Yn   (layer disimpan di mediator_layer)
        response  -> Z1, Z2, ..., Zn
    """

    ROLE_PREDICTOR = "predictor"
    ROLE_MEDIATOR = "mediator"
    ROLE_RESPONSE = "response"

    ROLE_CHOICES = [
        (ROLE_PREDICTOR, "Predictor"),
        (ROLE_MEDIATOR, "Mediator"),
        (ROLE_RESPONSE, "Response / Target"),
    ]

    ROLE_ORDER = {
        ROLE_PREDICTOR: 0,
        ROLE_MEDIATOR: 1,
        ROLE_RESPONSE: 2,
    }

    ROLE_CODE_PREFIX = {
        ROLE_PREDICTOR: "X",
        ROLE_MEDIATOR: "Y",
        ROLE_RESPONSE: "Z",
    }

    code = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name="Variable Code",
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Variable Name",
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description",
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        verbose_name="Weight",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_PREDICTOR,
        db_index=True,
        verbose_name="Role",
    )

    order = models.PositiveIntegerField(
        default=1,
        verbose_name="Order",
        help_text="Urutan variable di dalam rolenya.",
    )

    mediator_layer = models.ForeignKey(
        MediatorLayer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="variables",
        verbose_name="Mediator Layer",
        help_text="Layer mediator (1..N). Kosong untuk predictor/response.",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
    )

    class Meta:
        db_table = "master_variable"
        verbose_name = "Variable"
        verbose_name_plural = "Variables"
        # Tidak ada default ordering di sini — urutan yang benar
        # (role -> mediator_layer -> order) disediakan oleh
        # VariableConfigurationService.ordering().
        ordering = ["id"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        # ``code`` tidak diinput user (dibuat otomatis). Kalau kosong
        # (misal dibuat lewat admin/form tanpa code), isi placeholder
        # unik dulu; code final di-set oleh
        # VariableConfigurationService.regenerate_codes().
        if not self.code:
            self.code = f"T{uuid.uuid4().hex[:9]}"
        super().save(*args, **kwargs)

    @property
    def role_rank(self):
        return self.ROLE_ORDER.get(self.role, 0)

    @property
    def is_mediator(self):
        return self.role == self.ROLE_MEDIATOR
