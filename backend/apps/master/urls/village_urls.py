from django.urls import path

from apps.master.views import (
    VillageListView,
    VillageDetailView,
    VillageCreateView,
    VillageUpdateView,
    VillageDeleteView,
)

urlpatterns = [

    path(
        "village/",
        VillageListView.as_view(),
        name="village-list",
    ),

    path(
        "village/create/",
        VillageCreateView.as_view(),
        name="village-create",
    ),

    path(
        "village/<int:pk>/",
        VillageDetailView.as_view(),
        name="village-detail",
    ),

    path(
        "village/<int:pk>/update/",
        VillageUpdateView.as_view(),
        name="village-update",
    ),

    path(
        "village/<int:pk>/delete/",
        VillageDeleteView.as_view(),
        name="village-delete",
    ),

]