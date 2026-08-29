from apps.analytics.services.cluster_recommendation_service import (
    ClusterRecommendationService,
)
from apps.analytics.services.feature_importance_service import (
    FeatureImportanceService,
)
from apps.analytics.services.ml_dashboard_service import MLDashboardService


class ExportDataService:
    """
    Mengumpulkan seluruh data analytics jadi satu struktur,
    supaya Excel export & PDF export memakai sumber yang sama
    persis (DRY).
    """

    @classmethod
    def compile(cls):

        summary = MLDashboardService.summary()

        village_table = MLDashboardService.village_table()

        variable_importance = (
            FeatureImportanceService.dominant_variables()
        )

        dominant_indicators = (
            FeatureImportanceService.dominant_indicators(top_n=10)
        )

        cluster_ranking = (
            ClusterRecommendationService.rank_within_clusters()
        )

        narrative = MLDashboardService.narrative_summary(
            variable_importance,
        )

        top_village_row = (
            village_table[0] if village_table else None
        )

        radar_data = (
            FeatureImportanceService.radar_axes_for_village(
                top_village_row["village"]
            )
            if top_village_row
            else []
        )

        return {

            "summary": summary,

            "village_table": village_table,

            "variable_importance": variable_importance,

            "dominant_indicators": dominant_indicators,

            "cluster_ranking": cluster_ranking,

            "narrative": narrative,

            "representative_village": (
                top_village_row["village"]
                if top_village_row
                else None
            ),

            "radar_data": radar_data,

        }
