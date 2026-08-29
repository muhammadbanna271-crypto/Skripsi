from django.db.models import Avg

from apps.master.services.variable_configuration_service import (
    VariableConfigurationService,
)
from apps.recommendation.selectors.recommendation_selector import (
    RecommendationSelector,
)
from apps.response.models import Response


class AnalyticsSelector:
    """
    Menyiapkan feature matrix [desa x indikator] dari data historis
    Response, untuk dipakai training/prediksi ML.

    Sengaja memakai ulang RecommendationSelector.decision_matrix()
    (read-only) supaya definisi "skor indikator per desa" konsisten
    dengan yang dipakai TOPSIS di modul Recommendation -- tanpa
    mengubah kode di apps/recommendation sama sekali.
    """

    @staticmethod
    def indicators():

        return (
            RecommendationSelector.indicators()
        )

    @staticmethod
    def feature_matrix():
        """
        Return:
            villages    -> list[Village] (desa yang punya data historis)
            indicators  -> list[Indicator] (88 kolom fitur)
            matrix      -> list[list[float]] [n_desa x n_indikator]
        """

        villages, indicators, matrix = (
            RecommendationSelector.decision_matrix()
        )

        return villages, indicators, matrix

    @staticmethod
    def village_feature_vector(village):
        """
        Hitung 1 baris feature (rata-rata tiap indikator) untuk
        SATU desa saja -- dipakai saat prediksi desa baru.
        """

        indicators = list(
            VariableConfigurationService.active_indicators()
        )

        row = []

        for indicator in indicators:

            avg = (
                Response.objects
                .filter(
                    respondent__survey_village__village=village,
                    questionnaire__indicator=indicator,
                )
                .aggregate(
                    value=Avg("score")
                )["value"]
            )

            row.append(
                float(avg) if avg is not None else 0.0
            )

        return indicators, row
