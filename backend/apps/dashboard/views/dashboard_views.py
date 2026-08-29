from django.shortcuts import render

from apps.master.models import (
    Village,
    District,
    Cluster,
    Indicator,
)

from apps.respondent.models import Respondent
from apps.survey.models import Survey
from apps.response.models import Response

from apps.gis.views.gis_views import explore_page


def dashboard(request):
    """
    Halaman beranda (root ``/``).

    Visitor / anonymous -> landing "Explore" (asisten wisata + peta + destinasi).
    Staff / superuser   -> dashboard internal (KPI penelitian).
    """

    if not (request.user.is_staff or request.user.is_superuser):
        return explore_page(request)

    context = {
        "total_village": Village.objects.count(),
        "total_district": District.objects.count(),
        "total_cluster": Cluster.objects.count(),
        "total_indicator": Indicator.objects.count(),
        "total_respondent": Respondent.objects.count(),
        "total_survey": Survey.objects.count(),
        "total_response": Response.objects.count(),
    }

    return render(
        request,
        "dashboard/index.html",
        context,
    )
