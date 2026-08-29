from django.urls import path

from apps.survey.views import (
    SurveyListView,
    SurveyDetailView,
    SurveyCreateView,
    SurveyUpdateView,
    SurveyDeleteView,
)

urlpatterns = [

    path(
        "",
        SurveyListView.as_view(),
        name="survey-list",
    ),

    path(
        "create/",
        SurveyCreateView.as_view(),
        name="survey-create",
    ),

    path(
        "<int:pk>/",
        SurveyDetailView.as_view(),
        name="survey-detail",
    ),

    path(
        "<int:pk>/update/",
        SurveyUpdateView.as_view(),
        name="survey-update",
    ),

    path(
        "<int:pk>/delete/",
        SurveyDeleteView.as_view(),
        name="survey-delete",
    ),

]