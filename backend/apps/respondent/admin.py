from django.contrib import admin

from apps.respondent.models import Respondent


@admin.register(Respondent)
class RespondentAdmin(admin.ModelAdmin):

    list_display = (
        "nik",
        "name",
        "survey_village",
        "gender",
        "is_active",
    )

    list_filter = (
        "gender",
        "is_active",
    )

    search_fields = (
        "nik",
        "name",
    )