"""
Replace isi apps/recommendation/selectors/recommendation_selector.py
dengan ini. Logikanya sama persis, hasilnya sama persis -- cuma
caranya ambil data yang diubah dari N+1 query jadi 1 query.
"""

from django.db.models import Avg

from apps.master.models import Village
from apps.master.services.variable_configuration_service import (
    VariableConfigurationService,
)
from apps.response.models import Response


class RecommendationSelector:

    @staticmethod
    def villages():
        return (
            Village.objects
            .filter(is_active=True)
            .order_by("name")
        )

    @staticmethod
    def indicators():
        return VariableConfigurationService.active_indicators()

    @classmethod
    def decision_matrix(cls):
        villages = list(cls.villages())
        indicators = list(cls.indicators())

        # FIXED: satu query buat semua kombinasi desa x indikator,
        # bukan query terpisah per kombinasi (dulu: 30 desa x 88
        # indikator = 2.640 query; sekarang: 1 query).
        rows = (
            Response.objects
            .filter(
                respondent__survey_village__village__in=villages,
                questionnaire__indicator__in=indicators,
            )
            .values(
                "respondent__survey_village__village_id",
                "questionnaire__indicator_id",
            )
            .annotate(avg_score=Avg("score"))
        )

        lookup = {
            (
                row["respondent__survey_village__village_id"],
                row["questionnaire__indicator_id"],
            ): row["avg_score"]
            for row in rows
        }

        matrix = []

        for village in villages:
            row = []
            for indicator in indicators:
                avg = lookup.get((village.id, indicator.id), 0) or 0
                row.append(float(avg))
            matrix.append(row)

        return villages, indicators, matrix