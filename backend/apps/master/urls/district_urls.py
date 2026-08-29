from django.urls import path

from apps.master.views import (
    DistrictCreateView,
    DistrictDeleteView,
    DistrictDetailView,
    DistrictListView,
    DistrictUpdateView,
)

urlpatterns = [

    path(
        "district/",
        DistrictListView.as_view(),
        name="district-list",
    ),

    path(
        "district/create/",
        DistrictCreateView.as_view(),
        name="district-create",
    ),

    path(
        "district/<int:pk>/",
        DistrictDetailView.as_view(),
        name="district-detail",
    ),

    path(
        "district/<int:pk>/update/",
        DistrictUpdateView.as_view(),
        name="district-update",
    ),

    path(
        "district/<int:pk>/delete/",
        DistrictDeleteView.as_view(),
        name="district-delete",
    ),

]