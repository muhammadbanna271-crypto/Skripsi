from django.contrib import messages
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.db.models import IntegerField
from django.db.models.functions import Cast, Substr
from common.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from apps.master.forms import VillageForm
from apps.master.models import Village


class VillageListView(BaseListView):
    model = Village
    template_name = "master/village/list.html"
    context_object_name = "villages"

    ordering = ["code"]

    paginate_by = 10

    search_fields = [
        "code",
        "name",
        "district__name",
    ]

    def get_queryset(self):

        return (

            super()

            .get_queryset()

            .annotate(

                code_number=Cast(

                    "code",

                    IntegerField(),

                )   

            )

            .select_related(

                "district",

                "cluster",

            )

            .order_by(

                "code_number",

            )

        )


class VillageDetailView(BaseDetailView):
    model = Village
    template_name = "master/village/detail.html"
    context_object_name = "village"


class VillageCreateView(BaseCreateView):
    model = Village
    form_class = VillageForm
    template_name = "master/village/create.html"

    success_url = reverse_lazy("master:village-list")

    success_message = "Village created successfully."


class VillageUpdateView(BaseUpdateView):
    model = Village
    form_class = VillageForm
    template_name = "master/village/update.html"

    success_url = reverse_lazy("master:village-list")

    success_message = "Village updated successfully."


class VillageDeleteView(BaseDeleteView):
    model = Village
    template_name = "master/village/delete.html"

    success_url = reverse_lazy("master:village-list")

    success_message = "Village deleted successfully."

    def post(self, request, *args, **kwargs):

        self.object = self.get_object()

        try:

            self.object.delete()

            messages.success(
                request,
                "Village deleted successfully."
            )

        except ProtectedError:

            messages.error(
                request,
                "Village cannot be deleted because it is still being used."
            )

        except IntegrityError:

            messages.error(
                request,
                "Village cannot be deleted because it is still being used."
            )

        return redirect("master:village-list")