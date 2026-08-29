from django.contrib import admin

from apps.response.models import Response


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):

    list_display = (
        "respondent",
        "questionnaire",
        "score",
    )

    list_filter = (
        "questionnaire",
    )

    search_fields = (
        "respondent__name",
        "questionnaire__question",
    )