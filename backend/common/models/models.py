"""
File BARU: backend/common/models.py (atau tambahin ke file
common/models.py yang sudah ada kalau sudah ada isinya)
"""

from django.db import models


class SurveyAccessSetting(models.Model):
    """
    Singleton (cuma boleh ada 1 baris). Dikontrol superuser lewat
    Django admin. Kalau allow_public_input=True, user biasa
    (bukan staff) boleh input Survey/Respondent/Response. Kalau
    False (default), cuma staff/superuser yang boleh.
    """

    allow_public_input = models.BooleanField(
        default=False,
        verbose_name="Izinkan user biasa input data survey",
        help_text=(
            "Kalau dicentang, semua user yang login (termasuk "
            "yang bukan staff) boleh input Survey, Survey Village, "
            "Respondent, dan Response. Kalau tidak dicentang, "
            "cuma staff/superuser yang boleh."
        ),
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Survey Access Setting"
        verbose_name_plural = "Survey Access Setting"

    def __str__(self):
        return "Survey Access Setting"

    def save(self, *args, **kwargs):
        # Paksa cuma ada 1 baris (singleton pattern) -- selalu
        # pakai pk=1, apapun yang terjadi.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def is_public_input_allowed(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj.allow_public_input