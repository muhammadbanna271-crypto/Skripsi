from django.contrib import admin

from apps.survey.models import Survey


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "start_date",
        "end_date",
        "is_active",
    )

    search_fields = (
        "name",
    )

    list_filter = (
        "is_active",
    )