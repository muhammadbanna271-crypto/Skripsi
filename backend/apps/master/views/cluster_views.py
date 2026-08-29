from django.urls import reverse_lazy

from common.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)

from apps.master.forms import ClusterForm
from apps.master.models import Cluster


class ClusterListView(BaseListView):
    model = Cluster
    template_name = "master/cluster/list.html"
    context_object_name = "clusters"
    ordering = ["code"]
    search_fields = [
        "code",
        "name",
    ]


class ClusterDetailView(BaseDetailView):
    model = Cluster
    template_name = "master/cluster/detail.html"
    context_object_name = "cluster"


class ClusterCreateView(BaseCreateView):
    model = Cluster
    form_class = ClusterForm
    template_name = "master/cluster/create.html"
    success_url = reverse_lazy("master:cluster-list")
    success_message = "Cluster created successfully."


class ClusterUpdateView(BaseUpdateView):
    model = Cluster
    form_class = ClusterForm
    template_name = "master/cluster/update.html"
    success_url = reverse_lazy("master:cluster-list")
    success_message = "Cluster updated successfully."


class ClusterDeleteView(BaseDeleteView):
    model = Cluster
    template_name = "master/cluster/delete.html"
    success_url = reverse_lazy("master:cluster-list")
    success_message = "Cluster deleted successfully."