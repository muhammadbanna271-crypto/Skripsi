from django.urls import path

from apps.response.views import (
    ResponseListView,
    response_detail,
    ResponseCreateView,
    ResponseUpdateView,
    ResponseDeleteView,
    take_survey,
    import_response,
    delete_all_response,
)

urlpatterns = [

    path(
        "",
        ResponseListView.as_view(),
        name="response-list",
    ),

    path(
        "create/",
        ResponseCreateView.as_view(),
        name="response-create",
    ),

    path(
        "import/",
        import_response,
        name="response-import",
    ),

    path(
        "delete-all/",
        delete_all_response,
        name="response-delete-all",
    ),

    path(
        "survey/<int:respondent_id>/",
        take_survey,
        name="take-survey",
    ),

    path(
        "<int:respondent_id>/",
        response_detail,
        name="response-detail",
    ),

    path(
        "<int:pk>/update/",
        ResponseUpdateView.as_view(),
        name="response-update",
    ),

    path(
        "<int:pk>/delete/",
        ResponseDeleteView.as_view(),
        name="response-delete",
    ),

]