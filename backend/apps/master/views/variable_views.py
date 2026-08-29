from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from apps.analytics.models import AnalysisState

from common.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from apps.master.forms import VariableForm
from apps.master.models import MediatorLayer, Variable
from apps.master.services.variable_configuration_service import (
    VariableConfigurationService,
)


class VariableListView(BaseListView):
    model = Variable
    template_name = "master/variable/list.html"
    context_object_name = "variables"
    ordering = ["order"]
    search_fields = [
        "code",
        "name",
    ]

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related("mediator_layer")
            .order_by(*VariableConfigurationService.ordering())
        )


class VariableConfigurationPageView(LoginRequiredMixin, TemplateView):
    """
    Halaman drag-and-drop untuk mengatur konfigurasi variable
    (Predictor / Mediator / Response). Read-only untuk visitor.
    """

    template_name = "master/variable/config.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Tetapkan baseline signature kalau belum ada, supaya perubahan
        # yang dilakukan dari halaman ini bisa terdeteksi sebagai "stale".
        AnalysisState.ensure_baseline()

        config = VariableConfigurationService.load()
        layers = list(MediatorLayer.objects.order_by("number"))

        mediator_map = {}
        for layer_vars in config["mediator_layers"]:
            for item in layer_vars:
                mediator_map.setdefault(
                    item["mediator_layer"], []
                ).append(item)

        layer_panels = [
            {
                "id": layer.id,
                "number": layer.number,
                "name": layer.name,
                "is_active": layer.is_active,
                "variables": mediator_map.get(layer.number, []),
            }
            for layer in layers
        ]

        user = self.request.user
        context.update(
            {
                "predictors": config["predictors"],
                "responses": config["responses"],
                "layer_panels": layer_panels,
                "can_edit": user.is_staff or user.is_superuser,
                "errors": VariableConfigurationService.validate_configuration(),
            }
        )
        return context


class VariableDetailView(BaseDetailView):
    model = Variable
    template_name = "master/variable/detail.html"
    context_object_name = "variable"


class VariableCreateView(BaseCreateView):
    model = Variable
    form_class = VariableForm
    template_name = "master/variable/create.html"
    success_url = reverse_lazy("master:variable-list")
    success_message = "Variable created successfully."

    def form_valid(self, form):
        response = super().form_valid(form)
        VariableConfigurationService.regenerate_codes()
        return response


class VariableUpdateView(BaseUpdateView):
    model = Variable
    form_class = VariableForm
    template_name = "master/variable/update.html"
    success_url = reverse_lazy("master:variable-list")
    success_message = "Variable updated successfully."

    def form_valid(self, form):
        response = super().form_valid(form)
        VariableConfigurationService.regenerate_codes()
        return response


class VariableDeleteView(BaseDeleteView):
    model = Variable
    template_name = "master/variable/delete.html"
    success_url = reverse_lazy("master:variable-list")
    success_message = "Variable deleted successfully."