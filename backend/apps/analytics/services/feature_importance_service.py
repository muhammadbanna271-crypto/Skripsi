from apps.analytics.models import MLModelRegistry
from apps.master.models import Variable


class FeatureImportanceService:
    """
    Mengambil hasil feature importance (Random Forest) dari
    MLModelRegistry yang aktif, dan menyiapkannya untuk
    ditampilkan di dashboard (chart & radar).
    """

    @staticmethod
    def latest_registry():

        from apps.analytics.services.clustering_service import (
            ClusteringService,
        )

        return ClusteringService.ensure_trained()

    @classmethod
    def dominant_indicators(cls, top_n=10):

        registry = cls.latest_registry()

        if registry is None:
            return []

        return registry.feature_importance[:top_n]

    @classmethod
    def dominant_variables(cls):
        """
        Feature importance yang sudah diagregasi per variabel,
        dilengkapi nama variabel (bukan cuma code), cocok buat
        Feature Importance Chart & narasi kesimpulan otomatis.
        """

        registry = cls.latest_registry()

        if registry is None:
            return []

        variable_names = {
            variable.code: variable.name
            for variable in Variable.objects.all()
        }

        result = []

        for item in registry.variable_importance:

            result.append({

                "code": item["group"],

                "name": variable_names.get(
                    item["group"],
                    item["group"],
                ),

                "percentage": item["percentage"],

            })

        return result

    @classmethod
    def radar_axes_for_village(cls, village):
        """
        Nilai radar chart per desa: rata-rata skor tiap variabel
        (X.., Y.., Z..) diurutkan mengikuti konfigurasi role/layer/order.
        """

        scores = list(
            village.variable_scores
            .select_related("variable", "variable__mediator_layer")
        )

        scores.sort(
            key=lambda score: (
                score.variable.role_rank,
                (
                    score.variable.mediator_layer.number
                    if score.variable.mediator_layer
                    else 0
                ),
                score.variable.order,
            )
        )

        return [

            {

                "code": score.variable.code,

                "name": score.variable.name,

                "score": float(score.score),

            }

            for score in scores

        ]
