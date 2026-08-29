from django.contrib import messages
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from apps.master.models import Questionnaire
from apps.respondent.models import Respondent
from apps.response.forms import ResponseForm
from apps.response.models import Response
from django.shortcuts import redirect
from django.db.models.deletion import ProtectedError
from django.db import IntegrityError
from common.models.decorators import staff_required
from common.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseListView,
    BaseUpdateView,
)


class ResponseListView(BaseListView):

    model = Respondent

    template_name = "response/response/list.html"

    context_object_name = "respondents"

    paginate_by = 10
    search_fields = [
        "name",
    ]

    def get_queryset(self):

        queryset = super().get_queryset()

        queryset = (
            queryset
            .filter(responses__isnull=False)
            .annotate(
                total_question=Count("responses"),
                total_score=Sum("responses__score"),
            )
            .distinct()
            .order_by("name")
        )

        return queryset


@staff_required
def response_detail(request, respondent_id):

    respondent = get_object_or_404(
        Respondent,
        pk=respondent_id,
    )

    responses = (
        Response.objects
        .filter(respondent=respondent)
        .select_related(
            "questionnaire",
            "questionnaire__indicator",
        )
        .order_by(
            "questionnaire__indicator__variable__code",
            "questionnaire__indicator__code",
            "questionnaire__question_order",
        )
    )

    total_score = (
        responses.aggregate(
            total=Sum("score"),
        )["total"] or 0
    )

    return render(

        request,

        "response/response/detail.html",

        {

            "respondent": respondent,

            "responses": responses,

            "total_score": total_score,

        },

    )


class ResponseCreateView(BaseCreateView):

    model = Response

    form_class = ResponseForm

    template_name = "response/response/create.html"

    success_url = reverse_lazy("response:response-list")

    success_message = "Response created successfully."


class ResponseUpdateView(BaseUpdateView):

    model = Response

    form_class = ResponseForm

    template_name = "response/response/update.html"

    success_url = reverse_lazy("response:response-list")

    success_message = "Response updated successfully."


class ResponseDeleteView(BaseDeleteView):

    model = Response

    template_name = "response/response/delete.html"

    success_url = reverse_lazy("response:response-list")

    success_message = "Response deleted successfully."

    def post(self, request, *args, **kwargs):

        self.object = self.get_object()

        respondent_id = self.object.respondent.id

        try:

            self.object.delete()

            messages.success(
                request,
                "Response deleted successfully."
            )

        except (ProtectedError, IntegrityError):

            messages.error(
                request,
                "Response cannot be deleted."
            )

        return redirect(
            "response:response-detail",
            respondent_id=respondent_id,
        )

@staff_required
def take_survey(request, respondent_id):

    respondent = get_object_or_404(
        Respondent,
        pk=respondent_id,
    )

    questionnaires = (
        Questionnaire.objects
        .filter(is_active=True)
        .select_related(
            "indicator",
            "indicator__variable",
        )
        .order_by(
            "indicator__variable__code",
            "indicator__code",
            "question_order",
        )
    )

    if request.method == "POST":

        Response.objects.filter(
            respondent=respondent,
        ).delete()

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

                response.score = 5 if value == "1" else 1

            elif question.answer_type == "likert":

                response.answer_integer = int(value)

                response.score = int(value)

            elif question.answer_type == "integer":

                response.answer_integer = int(value)

                response.score = int(value)

            elif question.answer_type == "decimal":

                response.answer_decimal = float(value)

                response.score = float(value)

            elif question.answer_type == "text":

                response.answer_text = value

                response.score = 0

            elif question.answer_type == "choice":

                response.answer_text = value

                response.score = 0

            response.save()

        messages.success(
            request,
            "Survey berhasil disimpan."
        )

        return redirect(
            "respondent:respondent-list"
        )

    return render(

        request,

        "response/take_survey.html",

        {

            "respondent": respondent,

            "questionnaires": questionnaires,

        },

    )


def delete_all_response(request):

    # Hanya staff dan superuser yang boleh menghapus semua response
    if not request.user.is_authenticated:
        return redirect("login")

    if not (
        request.user.is_staff
        or request.user.is_superuser
    ):
        messages.error(
            request,
            "Anda tidak memiliki izin untuk menghapus semua response."
        )
        return redirect("response:response-list")

    if request.method == "POST":

        confirm_text = request.POST.get(
            "confirm_text",
            ""
        )

        if confirm_text.strip().upper() != "HAPUS":

            messages.error(
                request,
                (
                    'Konfirmasi tidak sesuai. Ketik "HAPUS" '
                    'persis untuk menghapus semua data response.'
                ),
            )

            return redirect(
                "response:response-list"
            )

        total = Response.objects.count()

        # Guard tambahan: kalau request kedua (mis. akibat double-submit
        # atau race condition) sampai lolos ke sini setelah data sudah
        # dihapus oleh request pertama, jangan tampilkan pesan sukses
        # "0 data" yang membingungkan seolah-olah ada dua proses hapus.
        if total == 0:

            messages.info(
                request,
                "Tidak ada data response untuk dihapus.",
            )

        else:

            Response.objects.all().delete()

            messages.success(
                request,
                f"{total} data response berhasil dihapus semua.",
            )

    return redirect(
        "response:response-list"
    )