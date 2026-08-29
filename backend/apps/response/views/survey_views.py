from django.shortcuts import redirect, render

from apps.master.models import Questionnaire
from apps.respondent.models import Respondent
from apps.response.models import Response
from apps.response.services import ResponseService
from apps.response.services import ScoringService

from apps.response.services import (
    ResponseService,
    ScoringService,
)

def take_survey(request, respondent_id):

    respondent = Respondent.objects.get(
        pk=respondent_id,
    )

    questionnaires = ResponseService.get_questionnaires()

    if request.method == "POST":

        for question in questionnaires:

            value = request.POST.get(
                f"question_{question.id}"
            )

            response = Response(
                respondent=respondent,
                questionnaire=question,
            )

            if question.answer_type == "boolean":

                response.answer_boolean = (
                    value == "1"
                )

            elif question.answer_type == "integer":

                if value:

                    response.answer_integer = int(value)

            elif question.answer_type == "decimal":

                if value:

                    response.answer_decimal = value

            else:

                response.answer_text = value

            response.save()

# Hitung skor setelah semua jawaban tersimpan
        ScoringService.calculate(
    respondent,
)

        return redirect(
            "respondent:respondent-list"
        )

    context = {

        "respondent": respondent,

        "questionnaires": questionnaires,

    }

    return render(

        request,

        "response/survey/form.html",

        context,

    )