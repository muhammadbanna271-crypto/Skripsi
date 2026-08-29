from django.conf import settings
from django.db import models

from common.models import BaseModel
from .variable import Variable


class VariableConfigAuditLog(BaseModel):
    """
    Audit log untuk perubahan konfigurasi variable (reorder/move/layer).
    Hanya untuk auditability — tidak mengganggu functionality utama.
    """

    ACTION_CHOICES = [
        ("reorder", "Reorder"),
        ("move", "Move"),
        ("add_layer", "Add Layer"),
        ("remove_layer", "Remove Layer"),
        ("deactivate_layer", "Deactivate Layer"),
        ("activate_layer", "Activate Layer"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="config_audit_logs",
        verbose_name="User",
    )

    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        verbose_name="Action",
    )

    variable = models.ForeignKey(
        Variable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="config_audit_logs",
        verbose_name="Variable",
    )

    old_role = models.CharField(
        max_length=20, blank=True, default="", verbose_name="Old Role"
    )
    new_role = models.CharField(
        max_length=20, blank=True, default="", verbose_name="New Role"
    )
    old_order = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Old Order"
    )
    new_order = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="New Order"
    )
    old_layer = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Old Layer"
    )
    new_layer = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="New Layer"
    )

    detail = models.JSONField(
        default=dict, blank=True, verbose_name="Detail"
    )

    class Meta:
        db_table = "master_variable_config_audit"
        verbose_name = "Variable Config Audit Log"
        verbose_name_plural = "Variable Config Audit Logs"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.action} - {self.variable} "
            f"({self.created_at:%Y-%m-%d %H:%M})"
        )
