from django.urls import path

from apps.master.views import (
    IndicatorCreateView,
    IndicatorDeleteView,
    IndicatorDetailView,
    IndicatorListView,
    IndicatorUpdateView,
    IndicatorByVariableView,
)

urlpatterns = [

    path(
        "indicators/",
        IndicatorListView.as_view(),
        name="indicator-list",
    ),

    path(
        "indicators/variable/<int:variable_id>/",
        IndicatorByVariableView.as_view(),
        name="indicator-by-variable",
    ),

    path(
        "indicators/create/",
        IndicatorCreateView.as_view(),
        name="indicator-create",
    ),

    path(
        "indicators/<int:pk>/",
        IndicatorDetailView.as_view(),
        name="indicator-detail",
    ),

    path(
        "indicators/<int:pk>/update/",
        IndicatorUpdateView.as_view(),
        name="indicator-update",
    ),

    path(
        "indicators/<int:pk>/delete/",
        IndicatorDeleteView.as_view(),
        name="indicator-delete",
    ),

]