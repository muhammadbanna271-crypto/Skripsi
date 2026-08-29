from django.db.models import Avg

from apps.respondent.models import Respondent
from apps.response.models import Response
from apps.master.models import Village
from apps.master.models import Questionnaire


def dashboard_summary():

    return {

        "total_respondent": Respondent.objects.count(),

        "total_questionnaire": Questionnaire.objects.count(),

        "total_village": Village.objects.count(),

        "total_response": Response.objects.count(),

        "average_score":

            Response.objects.aggregate(
                Avg("score")
            )["score__avg"] or 0,

    }