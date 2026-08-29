from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy

from common.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from apps.master.forms import QuestionnaireForm
from apps.master.models import (
    Questionnaire,
    Indicator,
    Variable,
)
from apps.master.services.variable_configuration_service import (
    VariableConfigurationService,
)


class QuestionnaireListView(BaseListView):

    model = Variable

    template_name = "master/questionnaire/list.html"

    context_object_name = "variables"

    paginate_by = 10

    ordering = ["order"]

    search_fields = [
        "code",
        "name",
    ]

    def get_queryset(self):

        queryset = (
            Variable.objects
            .select_related("mediator_layer")
            .annotate(
                indicator_count=Count(
                    "indicators",
                    distinct=True,
                ),
                questionnaire_count=Count(
                    "indicators__questionnaires",
                    distinct=True,
                ),
            )
            .order_by(*VariableConfigurationService.ordering())
        )

        q = self.request.GET.get("q")

        if q:
            queryset = queryset.filter(
                name__icontains=q
            )

        group = self.request.GET.get("group", "")

        queryset = VariableConfigurationService.filter_by_group(
            queryset, group
        )

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["group_options"] = (
            VariableConfigurationService.group_filter_options()
        )

        context["selected_group"] = self.request.GET.get("group", "")

        return context

class QuestionnaireByVariableView(BaseListView):
    """
    Menampilkan Indicator berdasarkan Variable.
    """

    model = Indicator

    template_name = "master/questionnaire/indicator_list.html"

    context_object_name = "indicators"

    paginate_by = 10

    def get_queryset(self):

        self.variable = get_object_or_404(
            Variable,
            pk=self.kwargs["variable_id"],
        )

        queryset = (
            Indicator.objects
            .filter(
                variable=self.variable,
            )
            .annotate(
                questionnaire_count=Count(
                    "questionnaires",
                    distinct=True,
                )
            )
            .order_by(
                "code",
            )
        )

        q = self.request.GET.get("q")

        if q:

            queryset = queryset.filter(
                name__icontains=q,
            )

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["variable"] = self.variable

        context["indicator_count"] = self.get_queryset().count()

        context["questionnaire_count"] = Questionnaire.objects.filter(
        indicator__variable=self.variable
        ).count()

        return context
    
class QuestionnaireByIndicatorView(BaseListView):
    """
    Menampilkan Questionnaire berdasarkan Indicator.
    """

    model = Questionnaire

    template_name = "master/questionnaire/questionnaire_list.html"

    context_object_name = "questionnaires"

    paginate_by = 10

    def get_queryset(self):

        self.indicator = get_object_or_404(
            Indicator,
            pk=self.kwargs["indicator_id"],
        )

        queryset = (
            Questionnaire.objects
            .select_related(
                "indicator",
            )
            .filter(
                indicator=self.indicator,
            )
            .order_by(
                "question_order",
            )
        )

        q = self.request.GET.get("q")

        if q:

            queryset = queryset.filter(
                question__icontains=q,
            )

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["indicator"] = self.indicator

        context["variable"] = self.indicator.variable

        context["questionnaire_count"] = self.get_queryset().count()

        return context

class QuestionnaireDetailView(BaseDetailView):
    model = Questionnaire
    template_name = "master/questionnaire/detail.html"
    context_object_name = "questionnaire"


class QuestionnaireCreateView(BaseCreateView):
    model = Questionnaire
    form_class = QuestionnaireForm
    template_name = "master/questionnaire/create.html"
    success_url = reverse_lazy("master:questionnaire-list")
    success_message = "Questionnaire created successfully."


class QuestionnaireUpdateView(BaseUpdateView):
    model = Questionnaire
    form_class = QuestionnaireForm
    template_name = "master/questionnaire/update.html"
    success_url = reverse_lazy("master:questionnaire-list")
    success_message = "Questionnaire updated successfully."


class QuestionnaireDeleteView(BaseDeleteView):
    model = Questionnaire
    template_name = "master/questionnaire/delete.html"
    success_url = reverse_lazy("master:questionnaire-list")
    success_message = "Questionnaire deleted successfully."

    def post(self, request, *args, **kwargs):

        self.object = self.get_object()

        try:

            self.object.delete()

            messages.success(
                request,
                "Questionnaire deleted successfully."
            )

        except (ProtectedError, IntegrityError):

            messages.error(
                request,
                "Questionnaire cannot be deleted because it is still being used."
            )

        return redirect("master:questionnaire-list")

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models.deletion import ProtectedError


class QuestionnaireDeleteAllView(LoginRequiredMixin, UserPassesTestMixin, View):

    template_name = "master/questionnaire/delete_all.html"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(
            self.request,
            "Kamu tidak punya izin untuk mengakses halaman ini.",
        )
        return redirect("dashboard:dashboard")

    def get(self, request, indicator_id):

        indicator = get_object_or_404(
            Indicator,
            pk=indicator_id,
        )

        questionnaires = Questionnaire.objects.filter(
            indicator=indicator,
        )

        return render(
            request,
            self.template_name,
            {
                "indicator": indicator,
                "questionnaires": questionnaires,
            },
        )

    def post(self, request, indicator_id):

        indicator = get_object_or_404(
            Indicator,
            pk=indicator_id,
        )

        confirmation = request.POST.get("confirmation")

        if confirmation != "HAPUS":

            messages.error(
                request,
                "Ketik HAPUS untuk menghapus seluruh questionnaire.",
            )

            return redirect(
                "master:questionnaire-delete-all",
                indicator.id,
            )

        questionnaires = Questionnaire.objects.filter(
            indicator=indicator,
        )

        try:

            questionnaires.delete()

            messages.success(
                request,
                "Semua questionnaire berhasil dihapus.",
            )

        except ProtectedError:

            messages.error(
                request,
                "Beberapa questionnaire masih digunakan sehingga tidak dapat dihapus.",
            )

        return redirect(
            "master:questionnaire-by-indicator",
            indicator.id,
        )