from django.db import models

from common.models import BaseModel


class MLModelRegistry(BaseModel):
    """
    Metadata setiap kali model clustering (K-Means) di-training ulang.

    Model fisik (scaler + kmeans) disimpan terpisah di
    apps/analytics/ml_models/*.joblib -- baris ini hanya
    menyimpan ringkasan hasil training terakhir supaya dashboard
    tidak perlu training ulang tiap kali halaman dibuka.
    """

    n_clusters = models.PositiveIntegerField(
        default=3,
    )

    n_samples = models.PositiveIntegerField(
        default=0,
    )

    silhouette_score = models.FloatField(
        null=True,
        blank=True,
    )

    inertia = models.FloatField(
        null=True,
        blank=True,
    )

    cluster_mapping = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Mapping label KMeans (0,1,2,...) ke Cluster master "
            "(id, code, name, rank, mean_score)."
        ),
    )

    feature_importance = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Hasil Random Forest feature importance per indikator, "
            "diurutkan dari yang paling dominan."
        ),
    )

    variable_importance = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Feature importance yang sudah diagregasi per variabel "
            "(X1, X2, ..., Y6) dalam bentuk persentase."
        ),
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Model registry aktif yang sedang dipakai sistem.",
    )

    class Meta:

        ordering = [
            "-created_at",
        ]

    def __str__(self):

        return (
            f"KMeans (k={self.n_clusters}) - "
            f"{self.created_at:%Y-%m-%d %H:%M}"
        )
