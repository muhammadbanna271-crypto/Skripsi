"""Helper untuk membuat data master di dalam test."""

import uuid

from apps.master.models import Indicator, MediatorLayer, Questionnaire, Variable


def create_variable(role, order=1, name=None, layer=None, is_active=True):
    return Variable.objects.create(
        code=f"T{uuid.uuid4().hex[:9]}",
        name=name or f"Var-{uuid.uuid4().hex[:6]}",
        role=role,
        order=order,
        mediator_layer=layer,
        is_active=is_active,
    )


def create_indicator(variable, code=None, name=None):
    return Indicator.objects.create(
        code=code or f"I{uuid.uuid4().hex[:9]}",
        name=name or f"Indicator-{uuid.uuid4().hex[:6]}",
        variable=variable,
    )


def create_questionnaire(indicator, question_order=1, question=None):
    return Questionnaire.objects.create(
        indicator=indicator,
        question=question or f"Q{question_order}",
        answer_type="likert",
        question_order=question_order,
    )
