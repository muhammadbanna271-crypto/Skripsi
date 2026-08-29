from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy

from common.models.decorators import staff_required
from common.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from apps.respondent.forms import RespondentForm
from apps.respondent.models import Respondent


class RespondentListView(BaseListView):

    model = Respondent

    template_name = "respondent/respondent/list.html"

    context_object_name = "respondents"

    ordering = [
        "name",
    ]

    paginate_by = 10
    
    search_fields = [
        "nik",
        "name",
        "survey_village__survey__name",
        "survey_village__village__name",
    ]

    def get_queryset(self):

        return (
            Respondent.objects
            .select_related(
                "survey_village",
                "survey_village__survey",
                "survey_village__village",
            )
            .order_by("name")
        )


class RespondentDetailView(BaseDetailView):

    model = Respondent

    template_name = "respondent/respondent/detail.html"

    context_object_name = "respondent"


class RespondentCreateView(BaseCreateView):

    model = Respondent

    form_class = RespondentForm

    template_name = "respondent/respondent/create.html"

    success_url = reverse_lazy("respondent:respondent-list")

    success_message = "Respondent created successfully."


class RespondentUpdateView(BaseUpdateView):

    model = Respondent

    form_class = RespondentForm

    template_name = "respondent/respondent/update.html"

    success_url = reverse_lazy("respondent:respondent-list")

    success_message = "Respondent updated successfully."


class RespondentDeleteView(BaseDeleteView):

    model = Respondent

    template_name = "respondent/respondent/delete.html"

    success_url = reverse_lazy("respondent:respondent-list")

    success_message = "Respondent deleted successfully."


@staff_required
def delete_all_respondent(request):

    if request.method == "POST":

        confirm_text = request.POST.get("confirm_text", "")

        if confirm_text.strip().upper() != "HAPUS":

            messages.error(
                request,
                (
                    "Konfirmasi tidak sesuai. Ketik \"HAPUS\" "
                    "persis untuk menghapus semua data respondent."
                ),
            )

            return redirect("respondent:respondent-list")

        total = Respondent.objects.count()

        Respondent.objects.all().delete()

        messages.success(
            request,
            (
                f"{total} data respondent (beserta seluruh "
                "response-nya) berhasil dihapus semua."
            ),
        )

    return redirect("respondent:respondent-list")