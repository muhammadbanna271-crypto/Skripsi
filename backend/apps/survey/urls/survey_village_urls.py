from django.urls import path

from apps.survey.views import (
    SurveyVillageListView,
    SurveyVillageCreateView,
    SurveyVillageUpdateView,
    SurveyVillageDeleteView,
)

urlpatterns = [

    path(
        "survey-village/",
        SurveyVillageListView.as_view(),
        name="survey-village-list",
    ),

    path(
        "survey-village/create/",
        SurveyVillageCreateView.as_view(),
        name="survey-village-create",
    ),

    path(
        "survey-village/<int:pk>/update/",
        SurveyVillageUpdateView.as_view(),
        name="survey-village-update",
    ),

    path(
        "survey-village/<int:pk>/delete/",
        SurveyVillageDeleteView.as_view(),
        name="survey-village-delete",
    ),

]