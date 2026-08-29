from django.urls import path

from apps.master.views import (
    QuestionnaireCreateView,
    QuestionnaireDeleteView,
    QuestionnaireDetailView,
    QuestionnaireListView,
    QuestionnaireUpdateView,
    QuestionnaireByVariableView,
    QuestionnaireByIndicatorView,
    QuestionnaireDeleteAllView,
)

urlpatterns = [

    # =========================
    # Variable Level
    # =========================

    path(
        "questionnaires/",
        QuestionnaireListView.as_view(),
        name="questionnaire-list",
    ),

    # =========================
    # Indicator Level
    # =========================

    path(
        "questionnaires/variable/<int:variable_id>/",
        QuestionnaireByVariableView.as_view(),
        name="questionnaire-by-variable",
    ),

    # =========================
    # Questionnaire Level
    # =========================

    path(
        "questionnaires/indicator/<int:indicator_id>/",
        QuestionnaireByIndicatorView.as_view(),
        name="questionnaire-by-indicator",
    ),

    path(
        "questionnaires/create/",
        QuestionnaireCreateView.as_view(),
        name="questionnaire-create",
    ),

    path(
    "questionnaires/indicator/<int:indicator_id>/delete-all/",
    QuestionnaireDeleteAllView.as_view(),
    name="questionnaire-delete-all",
    ),

    path(
        "questionnaires/<int:pk>/",
        QuestionnaireDetailView.as_view(),
        name="questionnaire-detail",
    ),

    path(
        "questionnaires/<int:pk>/update/",
        QuestionnaireUpdateView.as_view(),
        name="questionnaire-update",
    ),

    path(
        "questionnaires/<int:pk>/delete/",
        QuestionnaireDeleteView.as_view(),
        name="questionnaire-delete",
    ),

]