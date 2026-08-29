from django.urls import reverse_lazy

from common.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from apps.master.forms import DistrictForm
from apps.master.models import District


class DistrictListView(BaseListView):
    model = District
    template_name = "master/district/list.html"
    context_object_name = "districts"
    ordering = ["code"]
    search_fields = [
        "code",
        "name",
    ]


class DistrictDetailView(BaseDetailView):
    model = District
    template_name = "master/district/detail.html"
    context_object_name = "district"


class DistrictCreateView(BaseCreateView):
    model = District
    form_class = DistrictForm
    template_name = "master/district/create.html"
    success_url = reverse_lazy("master:district-list")
    success_message = "District created successfully."

class DistrictUpdateView(BaseUpdateView):
    model = District
    form_class = DistrictForm
    template_name = "master/district/update.html"
    success_url = reverse_lazy("master:district-list")
    success_message = "District updated successfully."


class DistrictDeleteView(BaseDeleteView):
    model = District
    template_name = "master/district/delete.html"
    success_url = reverse_lazy("master:district-list")
    success_message = "District deleted successfully."