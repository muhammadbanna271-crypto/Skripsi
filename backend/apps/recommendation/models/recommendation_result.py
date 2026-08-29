"""
File baru: apps/recommendation/models/recommendation_result.py
(tambahin juga import-nya ke apps/recommendation/models/__init__.py)
"""

from django.db import models


class RecommendationResult(models.Model):
    """
    Cache hasil perhitungan TOPSIS. Dihitung sekali lewat tombol
    "Hitung Ulang" (superuser only), lalu dibaca berkali-kali
    oleh siapapun yang buka dashboard -- tanpa hitung ulang.
    """

    computed_at = models.DateTimeField(auto_now=True)

    # Disimpan sebagai JSON: list of {village_id, village_name,
    # score, status, badge, recommendation}
    ranking = models.JSONField(default=list)

    n_villages = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Recommendation Result (cache)"

    def __str__(self):
        return f"TOPSIS result @ {self.computed_at:%Y-%m-%d %H:%M}"