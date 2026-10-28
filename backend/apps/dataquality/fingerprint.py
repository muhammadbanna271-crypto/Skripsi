"""
Sidik jari keadaan database untuk uji determinisme dan idempotensi.

Timestamp (created_at/updated_at) dan primary key tidak ikut di-hash.
"""

import hashlib
import json
from decimal import Decimal

from apps.analytics.models import IndicatorScore, VariableScore, VillageScore
from apps.respondent.models import Respondent
from apps.response.models import Response


def _norm(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if value is None:
        return None
    return str(value)


def _digest(rows):
    payload = json.dumps(rows, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def respondent_rows():
    return sorted(
        [
            _norm(nik),
            _norm(village_code),
            _norm(name),
            _norm(gender),
            _norm(birth_date),
            _norm(address),
        ]
        for nik, village_code, name, gender, birth_date, address in (
            Respondent.objects.values_list(
                "nik",
                "survey_village__village__code",
                "name",
                "gender",
                "birth_date",
                "address",
            )
        )
    )


def answer_rows():
    """Tabel jawaban, terurut."""
    return sorted(
        [
            _norm(nik),
            _norm(indicator_code),
            _norm(boolean),
            _norm(integer),
            _norm(decimal),
            _norm(text),
            _norm(score),
        ]
        for nik, indicator_code, boolean, integer, decimal, text, score in (
            Response.objects.values_list(
                "respondent__nik",
                "questionnaire__indicator__code",
                "answer_boolean",
                "answer_integer",
                "answer_decimal",
                "answer_text",
                "score",
            )
        )
    )


def score_rows():
    """Tabel skor agregat (indikator, variabel, desa), terurut."""

    rows = [
        ["indicator", village, code, _norm(score)]
        for village, code, score in IndicatorScore.objects.values_list(
            "village__code", "indicator__code", "score"
        )
    ]
    rows += [
        ["variable", village, code, _norm(score)]
        for village, code, score in VariableScore.objects.values_list(
            "village__code", "variable__code", "score"
        )
    ]
    rows += [
        ["village", village, "", f"{_norm(total)}|{_norm(normalized)}|{rank}"]
        for village, total, normalized, rank in (
            VillageScore.objects.values_list(
                "village__code", "total_score", "normalized_score", "rank"
            )
        )
    ]
    return sorted(rows)


def database_state():
    """Ringkasan hash + jumlah record; dua keadaan sama bila dict-nya sama."""

    respondents = respondent_rows()
    answers = answer_rows()
    scores = score_rows()

    return {
        "n_respondents": len(respondents),
        "n_answers": len(answers),
        "n_scores": len(scores),
        "respondents_sha256": _digest(respondents),
        "answers_sha256": _digest(answers),
        "scores_sha256": _digest(scores),
    }
