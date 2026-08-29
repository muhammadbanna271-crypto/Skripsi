from django.urls import path

from apps.master.views import (
    VariableConfigurationPageView,
    VariableCreateView,
    VariableDeleteView,
    VariableDetailView,
    VariableListView,
    VariableUpdateView,
)

urlpatterns = [

    path(
        "variables/",
        VariableListView.as_view(),
        name="variable-list",
    ),

    path(
        "variables/configure/",
        VariableConfigurationPageView.as_view(),
        name="variable-config-page",
    ),

    path(
        "variables/create/",
        VariableCreateView.as_view(),
        name="variable-create",
    ),

    path(
        "variables/<int:pk>/",
        VariableDetailView.as_view(),
        name="variable-detail",
    ),

    path(
        "variables/<int:pk>/update/",
        VariableUpdateView.as_view(),
        name="variable-update",
    ),

    path(
        "variables/<int:pk>/delete/",
        VariableDeleteView.as_view(),
        name="variable-delete",
    ),

]