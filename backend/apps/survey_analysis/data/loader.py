"""Memuat respons Likert dari DB menjadi matriks responden × item.

Source of truth data adalah model Django (master.Questionnaire +
response.Response). Loader mem-pivot respons menjadi DataFrame pandas dengan
index = respondent_id dan kolom = kode item Likert (mis. "X1.1").
"""

import pandas as pd

from apps.master.models import Questionnaire
from apps.response.models import Response
from apps.survey_analysis.config import model_config


def load_item_map():
    """Mapping item Likert -> {code, question, variable} (terurut)."""
    qs = (
        Questionnaire.objects
        .filter(answer_type="likert", is_active=True)
        .select_related("indicator__variable")
        .order_by("indicator__code")
    )
    return [
        {
            "code": q.indicator.code,
            "question": q.question,
            "variable": q.indicator.variable.code,
        }
        for q in qs
    ]


def load_response_matrix():
    """Pivot Response -> DataFrame (index=respondent_id, kolom=item code).

    Kolom diurutkan sesuai urutan item di model_config (X1.1 ... Z3.8).
    Nilai = answer_integer (skor Likert 1-5).
    """
    rows = (
        Response.objects
        .filter(
            questionnaire__answer_type="likert",
            answer_integer__isnull=False,
        )
        .values_list(
            "respondent_id",
            "questionnaire__indicator__code",
            "answer_integer",
        )
    )
    df = pd.DataFrame(
        list(rows),
        columns=["respondent_id", "item", "value"],
    )
    if df.empty:
        return pd.DataFrame(columns=model_config.all_items())

    # pivot_table('first') aman bila ada duplikat (responden, item) tak terduga.
    matrix = df.pivot_table(
        index="respondent_id",
        columns="item",
        values="value",
        aggfunc="first",
    )
    matrix = matrix.reindex(columns=model_config.all_items())
    matrix.index.name = "respondent_id"
    return matrix


def load_dataset():
    """Muat matriks + metadata ringkas (untuk validasi & tahap berikutnya)."""
    matrix = load_response_matrix()
    items = load_item_map()
    return {
        "matrix": matrix,
        "items": items,
        "n_respondents": int(matrix.shape[0]),
        "n_items": int(matrix.shape[1]),
    }
