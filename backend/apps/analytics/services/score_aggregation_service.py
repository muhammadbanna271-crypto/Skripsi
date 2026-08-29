from django.db import transaction

from apps.analytics.models import (
    IndicatorScore,
    VariableScore,
    VillageScore,
)
from apps.analytics.selectors.analytics_selector import AnalyticsSelector


class ScoreAggregationService:
    """
    Mengubah data historis di tabel Response menjadi skor agregat
    per desa: IndicatorScore -> VariableScore -> VillageScore.

    Ini dijalankan sebelum clustering, supaya feature matrix ML
    dan tampilan (radar chart, dsb) berasal dari sumber yang sama.
    """

    @classmethod
    @transaction.atomic
    def populate_all(cls):

        villages, indicators, matrix = (
            AnalyticsSelector.feature_matrix()
        )

        village_variable_totals = {}

        for village, row in zip(villages, matrix):

            variable_totals = {}

            for indicator, score in zip(indicators, row):

                IndicatorScore.objects.update_or_create(
                    village=village,
                    indicator=indicator,
                    defaults={"score": round(score, 2)},
                )

                variable = indicator.variable

                bucket = variable_totals.setdefault(
                    variable.id,
                    {"variable": variable, "scores": []},
                )

                bucket["scores"].append(score)

            village_variable_totals[village.id] = (
                village,
                variable_totals,
            )

        village_totals = []

        for village_id, (village, variable_totals) in (
            village_variable_totals.items()
        ):

            variable_means = []

            for bucket in variable_totals.values():

                mean_score = (
                    sum(bucket["scores"])
                    / len(bucket["scores"])
                    if bucket["scores"]
                    else 0
                )

                variable_means.append(mean_score)

                VariableScore.objects.update_or_create(
                    village=village,
                    variable=bucket["variable"],
                    defaults={"score": round(mean_score, 2)},
                )

            total_score = sum(variable_means)

            max_possible = 5 * len(variable_means) if variable_means else 1

            normalized = (
                total_score / max_possible
                if max_possible
                else 0
            )

            village_totals.append(
                (village, total_score, normalized)
            )

        village_totals.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        for rank, (village, total_score, normalized) in enumerate(
            village_totals,
            start=1,
        ):

            VillageScore.objects.update_or_create(
                village=village,
                defaults={
                    "total_score": round(total_score, 2),
                    "normalized_score": round(normalized, 4),
                    "rank": rank,
                },
            )

        return len(village_totals)
