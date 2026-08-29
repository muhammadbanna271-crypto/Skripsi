from django.urls import reverse_lazy

from common.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseListView,
    BaseUpdateView,
)

from apps.survey.models import SurveyVillage
from apps.survey.forms import SurveyVillageForm


class SurveyVillageListView(BaseListView):

    model = SurveyVillage

    template_name = "survey_village/list.html"

    context_object_name = "object_list"

    paginate_by = 10

    queryset = (
        SurveyVillage.objects
        .select_related(
            "survey",
            "village",
        )
        .order_by(
            "survey__name",
            "village__name",
        )
    )


class SurveyVillageCreateView(BaseCreateView):

    model = SurveyVillage

    form_class = SurveyVillageForm

    template_name = "survey_village/create.html"

    success_url = reverse_lazy(
        "survey:survey-village-list"
    )

    success_message = "Survey village created successfully."


class SurveyVillageUpdateView(BaseUpdateView):

    model = SurveyVillage

    form_class = SurveyVillageForm

    template_name = "survey_village/update.html"

    success_url = reverse_lazy(
        "survey:survey-village-list"
    )

    success_message = "Survey village updated successfully."


class SurveyVillageDeleteView(BaseDeleteView):

    model = SurveyVillage

    template_name = "survey_village/delete.html"

    success_url = reverse_lazy(
        "survey:survey-village-list"
    )

    success_message = "Survey village deleted successfully."
