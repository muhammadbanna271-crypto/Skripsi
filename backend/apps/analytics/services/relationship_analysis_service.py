"""Analisis relasi ringan predictor -> response.

Config-driven & variable-agnostic: daftar predictor/response diambil
dari VariableConfigurationService (bukan hard-coded), sehingga berubah
otomatis mengikuti konfigurasi. Mediator tidak ikut dihitung di sini —
relasi dihitung langsung X -> Z (atau Y -> Z kalau role berubah).
"""

import numpy as np

from apps.analytics.models import VariableScore
from apps.master.services.variable_configuration_service import (
    VariableConfigurationService,
)


class RelationshipAnalysisService:

    @staticmethod
    def run():
        """Korelasi Pearson antara skor tiap predictor dan tiap response,
        dihitung antar desa dari VariableScore yang sudah teragregasi.

        Return list of dict: [{predictor, response, correlation, n}]
        """
        config = VariableConfigurationService.load()

        predictors = [
            (item["id"], item["code"]) for item in config["predictors"]
        ]
        responses = [
            (item["id"], item["code"]) for item in config["responses"]
        ]

        if not predictors or not responses:
            return []

        variable_ids = [pid for pid, _ in predictors] + [
            rid for rid, _ in responses
        ]

        # village_id -> {variable_id: score}
        village_rows = {}

        scores = VariableScore.objects.select_related("variable").filter(
            variable_id__in=variable_ids
        )

        for score in scores:
            village_rows.setdefault(score.village_id, {})[
                score.variable_id
            ] = float(score.score)

        code_by_id = {
            pid: code for pid, code in predictors + responses
        }

        result = []

        for predictor_id, predictor_code in predictors:
            for response_id, response_code in responses:
                xs = []
                ys = []

                for row in village_rows.values():
                    if predictor_id in row and response_id in row:
                        xs.append(row[predictor_id])
                        ys.append(row[response_id])

                correlation = None

                if len(xs) >= 2:
                    # Bisa NaN kalau variance salah satu sisi = 0.
                    value = float(np.corrcoef(xs, ys)[0, 1])
                    correlation = (
                        None if np.isnan(value) else round(value, 4)
                    )

                result.append(
                    {
                        "predictor": predictor_code,
                        "response": response_code,
                        "correlation": correlation,
                        "n": len(xs),
                    }
                )

        return result
