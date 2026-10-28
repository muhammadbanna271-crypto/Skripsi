"""Master data + workbook sintetis (88 indikator X1.1..Y6.8) untuk test."""

import datetime
import random
from io import BytesIO

from django.test import TestCase
from openpyxl import Workbook

from apps.master.models import (
    District,
    Indicator,
    Questionnaire,
    Variable,
    Village,
)
from apps.survey.models import Survey

N_VILLAGES = 6
N_ROWS = 24
PERSONS = ["Kades", "Sekdes", "Ketua RT", "Tokoh"]

# X1..X5 (5 x 8) + Y1..Y6 (6 x 8) = 88 indikator.
VARIABLES = [(f"X{i}", "predictor") for i in range(1, 6)] + [
    (f"Y{i}", "response") for i in range(1, 7)
]

INDICATOR_CODES = [
    f"{var}.{n}" for var, _ in VARIABLES for n in range(1, 9)
]

assert len(INDICATOR_CODES) == 88


def build_master():
    district = District.objects.create(code="DQ", name="Distrik DQ")

    for number in range(1, N_VILLAGES + 1):
        Village.objects.create(
            code=str(number), name=f"Desa {number}", district=district
        )

    for order, (code, role) in enumerate(VARIABLES, start=1):
        variable = Variable.objects.create(
            code=code, name=f"Var {code}", role=role, order=order
        )
        for n in range(1, 9):
            indicator = Indicator.objects.create(
                code=f"{code}.{n}", name=f"Ind {code}.{n}", variable=variable
            )
            Questionnaire.objects.create(
                indicator=indicator,
                question=f"Q {code}.{n}",
                answer_type="likert",
                question_order=n,
            )


def clean_rows(seed=7):
    rng = random.Random(seed)
    rows = []
    for i in range(N_ROWS):
        rows.append(
            [i + 1, i + 1, (i % N_VILLAGES) + 1, i // N_VILLAGES + 1,
             PERSONS[i % len(PERSONS)]]
            + [rng.randint(1, 5) for _ in INDICATOR_CODES]
        )
    return rows


def make_workbook(mutate=None):
    """Return bytes workbook bersih; mutate(ws) boleh merusak sel tertentu."""

    wb = Workbook()
    ws = wb.active
    ws.append(["No", "ID Resp", "Desa", "RT", "Person"] + INDICATOR_CODES)
    for row in clean_rows():
        ws.append(row)

    if mutate:
        mutate(ws)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# Posisi sel pada workbook sintetis: baris data pertama = 2.
COL_ID, COL_DESA, COL_RT, COL_PERSON = 2, 3, 4, 5
FIRST_INDICATOR_COL = 6


class DQTestCase(TestCase):

    def setUp(self):
        build_master()
        self.survey = Survey.objects.create(
            name="Survey DQ",
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2024, 12, 31),
        )
