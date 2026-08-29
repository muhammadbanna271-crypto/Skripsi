from django.urls import reverse_lazy

from common.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from apps.survey.forms import SurveyForm
from apps.survey.models import Survey
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum
from apps.survey.models import Survey


class SurveyListView(BaseListView):

    model = Survey

    template_name = "survey/survey/list.html"

    context_object_name = "surveys"

    ordering = [
        "-start_date",
    ]

    search_fields = [
        "name",
    ]


class SurveyDetailView(BaseDetailView):

    model = Survey

    template_name = "survey/survey/detail.html"

    context_object_name = "survey"


class SurveyCreateView(BaseCreateView):

    model = Survey

    form_class = SurveyForm

    template_name = "survey/survey/create.html"

    success_url = reverse_lazy("survey:survey-list")

    success_message = "Survey created successfully."


class SurveyUpdateView(BaseUpdateView):

    model = Survey

    form_class = SurveyForm

    template_name = "survey/survey/update.html"

    success_url = reverse_lazy("survey:survey-list")

    success_message = "Survey updated successfully."


class SurveyDeleteView(BaseDeleteView):

    model = Survey

    template_name = "survey/survey/delete.html"

    success_url = reverse_lazy("survey:survey-list")

    success_message = "Survey deleted successfully."

