from django.urls import path

from apps.master.views import (
    ClusterCreateView,
    ClusterDeleteView,
    ClusterDetailView,
    ClusterListView,
    ClusterUpdateView,
)

urlpatterns = [

    path(
        "clusters/",
        ClusterListView.as_view(),
        name="cluster-list",
    ),

    path(
        "clusters/create/",
        ClusterCreateView.as_view(),
        name="cluster-create",
    ),

    path(
        "clusters/<int:pk>/",
        ClusterDetailView.as_view(),
        name="cluster-detail",
    ),

    path(
        "clusters/<int:pk>/update/",
        ClusterUpdateView.as_view(),
        name="cluster-update",
    ),

    path(
        "clusters/<int:pk>/delete/",
        ClusterDeleteView.as_view(),
        name="cluster-delete",
    ),

]