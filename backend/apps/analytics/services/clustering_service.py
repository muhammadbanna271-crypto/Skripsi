import numpy as np
from django.db import transaction

from apps.analytics.ml.clustering import KMeansClusterModel
from apps.analytics.ml.feature_importance import (
    aggregate_importance_by_group,
    compute_feature_importance,
)
from apps.analytics.models import MLModelRegistry
from apps.analytics.selectors.analytics_selector import AnalyticsSelector
from apps.analytics.services.score_aggregation_service import (
    ScoreAggregationService,
)
from apps.master.models import Cluster


LEVEL_NAMES = [
    "Unggul",
    "Sedang",
    "Berkembang",
    "Rendah",
    "Sangat Rendah",
]


class ClusteringService:

    N_CLUSTERS = 3

    # =========================================================
    # TRAINING (atas seluruh data historis, unsupervised,
    # TIDAK ada train/test split)
    # =========================================================

    @classmethod
    @transaction.atomic
    def train_and_save(cls):

        villages, indicators, matrix = (
            AnalyticsSelector.feature_matrix()
        )

        if not villages or not matrix:

            return {
                "success": False,
                "message": (
                    "Belum ada data Response yang cukup untuk "
                    "melakukan clustering."
                ),
            }

        ScoreAggregationService.populate_all()

        X = np.array(matrix, dtype=float)

        cluster_model = KMeansClusterModel(
            n_clusters=cls.N_CLUSTERS,
        )

        fit_result = cluster_model.fit(X)

        cluster_model.save()

        labels = fit_result["labels"]

        cluster_mapping = cls._map_labels_to_master_cluster(
            X,
            labels,
        )

        cls._assign_village_cluster(
            villages,
            labels,
            cluster_mapping,
        )

        feature_names = [
            indicator.code for indicator in indicators
        ]

        feature_importance = compute_feature_importance(
            X,
            labels,
            feature_names,
        )

        feature_to_variable = {
            indicator.code: indicator.variable.code
            for indicator in indicators
        }

        variable_importance = aggregate_importance_by_group(
            feature_importance,
            feature_to_variable,
        )

        MLModelRegistry.objects.filter(
            is_active=True,
        ).update(
            is_active=False,
        )

        registry = MLModelRegistry.objects.create(
            n_clusters=cls.N_CLUSTERS,
            n_samples=len(villages),
            silhouette_score=fit_result["silhouette_score"],
            inertia=fit_result["inertia"],
            cluster_mapping=cluster_mapping,
            feature_importance=feature_importance,
            variable_importance=variable_importance,
            is_active=True,
        )

        # Model sudah di-train ulang -> simpan signature konfigurasi.
        from apps.analytics.models import AnalysisState

        AnalysisState.mark_computed()

        return {

            "success": True,

            "registry": registry,

            "n_villages": len(villages),

            "silhouette_score": fit_result["silhouette_score"],

        }

    @classmethod
    def ensure_trained(cls):
        """Ambil MLModelRegistry aktif; latih model kalau belum ada.

        Fallback lazy supaya chatbot/dashboard tetap punya data (clustering,
        feature importance) walau admin belum klik "Retrain Model" manual.
        Kalau sudah ada registry aktif, cukup dibaca (tanpa latih ulang).
        """
        registry = (
            MLModelRegistry.objects
            .filter(is_active=True)
            .first()
        )

        if registry is None:
            cls.train_and_save()
            registry = (
                MLModelRegistry.objects
                .filter(is_active=True)
                .first()
            )

        return registry

    # =========================================================
    # Pemetaan label KMeans (0,1,2,...) -> Cluster master data,
    # diberi nama berdasarkan ranking rata-rata skor
    # (cluster paling tinggi = "Unggul", dst).
    # =========================================================

    @classmethod
    def _map_labels_to_master_cluster(cls, X, labels):

        labels = np.array(labels)

        unique_labels = sorted(set(labels.tolist()))

        cluster_means = {}

        for label in unique_labels:

            rows = X[labels == label]

            cluster_means[label] = float(rows.mean())

        ranked = sorted(
            unique_labels,
            key=lambda label: cluster_means[label],
            reverse=True,
        )

        mapping = {}

        for rank, label in enumerate(ranked):

            level_name = (
                LEVEL_NAMES[rank]
                if rank < len(LEVEL_NAMES)
                else f"Cluster {rank + 1}"
            )

            code = f"AUTOK{rank + 1}"

            cluster_obj, _ = Cluster.objects.get_or_create(
                code=code,
                defaults={
                    "name": f"{level_name} (Auto K-Means)",
                    "description": (
                        "Dibentuk otomatis oleh model K-Means "
                        "berdasarkan hasil clustering desa."
                    ),
                },
            )

            mapping[str(label)] = {

                "cluster_id": cluster_obj.id,

                "code": cluster_obj.code,

                "name": cluster_obj.name,

                "rank": rank + 1,

                "mean_score": round(cluster_means[label], 3),

            }

        return mapping

    @staticmethod
    def _assign_village_cluster(villages, labels, cluster_mapping):

        for village, label in zip(villages, labels):

            info = cluster_mapping[str(label)]

            village.cluster_id = info["cluster_id"]

            village.save(
                update_fields=["cluster"],
            )

    # =========================================================
    # PREDIKSI DESA BARU -- hanya .predict(), tidak fit ulang
    # =========================================================

    @classmethod
    def predict_village(cls, village):

        cluster_model = KMeansClusterModel.load()

        if cluster_model is None:

            return {
                "success": False,
                "message": (
                    "Model clustering belum pernah di-training. "
                    "Jalankan training terlebih dahulu."
                ),
            }

        registry = (
            MLModelRegistry.objects
            .filter(is_active=True)
            .first()
        )

        if registry is None:

            return {
                "success": False,
                "message": "Registry model tidak ditemukan.",
            }

        indicators, row = AnalyticsSelector.village_feature_vector(
            village,
        )

        predicted_label = cluster_model.predict([row])[0]

        info = registry.cluster_mapping.get(
            str(predicted_label)
        )

        if info is None:

            return {
                "success": False,
                "message": "Label cluster tidak dikenali di registry.",
            }

        village.cluster_id = info["cluster_id"]

        village.save(
            update_fields=["cluster"],
        )

        return {

            "success": True,

            "village": village,

            "cluster": info,

            "feature_vector": row,

        }

    # =========================================================
    # SIMULASI MANUAL -- input skor per Variabel (bukan dari
    # desa/survey riil), tetap hanya .predict(), tidak fit ulang.
    # =========================================================

    @classmethod
    def predict_manual(cls, variable_scores):
        """
        variable_scores: dict {variable_code: skor (1-5)}

        Karena model dilatih di level indikator (88 kolom), tiap
        indikator dalam satu variabel diberi nilai yang sama
        dengan skor variabelnya (pendekatan/approximation untuk
        simulasi cepat, bukan pengganti survey riil).
        """

        cluster_model = KMeansClusterModel.load()

        if cluster_model is None:

            return {
                "success": False,
                "message": (
                    "Model clustering belum pernah di-training. "
                    "Jalankan training terlebih dahulu."
                ),
            }

        registry = (
            MLModelRegistry.objects
            .filter(is_active=True)
            .first()
        )

        if registry is None:

            return {
                "success": False,
                "message": "Registry model tidak ditemukan.",
            }

        indicators = AnalyticsSelector.indicators()

        row = [
            float(variable_scores.get(indicator.variable.code, 0))
            for indicator in indicators
        ]

        predicted_label = cluster_model.predict([row])[0]

        info = registry.cluster_mapping.get(
            str(predicted_label)
        )

        if info is None:

            return {
                "success": False,
                "message": "Label cluster tidak dikenali di registry.",
            }

        return {

            "success": True,

            "cluster": info,

            "feature_vector": row,

        }

