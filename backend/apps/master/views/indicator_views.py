from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from apps.master.models import Indicator, Variable
from common.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from apps.master.forms import IndicatorForm
from apps.master.models import Indicator, Variable
from apps.master.services.variable_configuration_service import (
    VariableConfigurationService,
)


class IndicatorListView(BaseListView):
    """
    Menampilkan Variable sebagai group Indicator,
    urut mengikuti Variable Configuration.
    """

    model = Variable

    template_name = "master/indicator/list.html"

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
                indicator_count=Count("indicators")
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

class IndicatorByVariableView(BaseListView):
    """
    Menampilkan seluruh indicator berdasarkan variable
    """

    model = Indicator

    template_name = "master/indicator/detail_list.html"

    context_object_name = "indicators"

    paginate_by = 10

    search_fields = [
        "code",
        "name",
    ]

    def get_queryset(self):

        self.variable = get_object_or_404(
            Variable,
            pk=self.kwargs["variable_id"],
        )

        queryset = (
            Indicator.objects
            .select_related("variable")
            .filter(variable=self.variable)
            .order_by("code")
        )

        q = self.request.GET.get("q")

        if q:

            queryset = queryset.filter(
                name__icontains=q
            )

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["variable"] = self.variable

        context["indicator_count"] = self.get_queryset().count()

        return context

class IndicatorDetailView(BaseDetailView):
    model = Indicator
    template_name = "master/indicator/detail.html"
    context_object_name = "indicator"


class IndicatorCreateView(BaseCreateView):
    model = Indicator
    form_class = IndicatorForm
    template_name = "master/indicator/create.html"

    success_url = reverse_lazy("master:indicator-list")

    success_message = "Indicator created successfully."


class IndicatorUpdateView(BaseUpdateView):
    model = Indicator
    form_class = IndicatorForm
    template_name = "master/indicator/update.html"

    success_url = reverse_lazy("master:indicator-list")

    success_message = "Indicator updated successfully."


class IndicatorDeleteView(BaseDeleteView):
    model = Indicator

    template_name = "master/indicator/delete.html"

    success_url = reverse_lazy("master:indicator-list")

    success_message = "Indicator deleted successfully."

    def post(self, request, *args, **kwargs):

        self.object = self.get_object()

        try:

            self.object.delete()

            messages.success(
                request,
                "Indicator deleted successfully."
            )

        except (ProtectedError, IntegrityError):

            messages.error(
                request,
                "Indicator cannot be deleted because it is still being used."
            )

        return redirect("master:indicator-list")