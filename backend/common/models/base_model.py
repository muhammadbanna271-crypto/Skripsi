from django.db import models

from common.managers import BaseManager


class BaseModel(models.Model):
    """
    Abstract base model.
    Every model in the project will inherit from this class.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    objects = BaseManager()

    class Meta:
        abstract = True