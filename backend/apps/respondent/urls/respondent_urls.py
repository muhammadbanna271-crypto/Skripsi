from django.urls import path

from apps.respondent.views import (
    RespondentListView,
    RespondentDetailView,
    RespondentCreateView,
    RespondentUpdateView,
    RespondentDeleteView,
    delete_all_respondent,
)

urlpatterns = [

    path(
        "",
        RespondentListView.as_view(),
        name="respondent-list",
    ),

    path(
        "create/",
        RespondentCreateView.as_view(),
        name="respondent-create",
    ),

    path(
        "delete-all/",
        delete_all_respondent,
        name="respondent-delete-all",
    ),

    path(
        "<int:pk>/",
        RespondentDetailView.as_view(),
        name="respondent-detail",
    ),

    path(
        "<int:pk>/update/",
        RespondentUpdateView.as_view(),
        name="respondent-update",
    ),

    path(
        "<int:pk>/delete/",
        RespondentDeleteView.as_view(),
        name="respondent-delete",
    ),

]