from django.contrib import admin

from apps.master.models import Questionnaire

@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = (
        "indicator",
        "question_order",
        "answer_type",
        "is_required",
        "is_active",
    )

    list_filter = (
        "answer_type",
        "is_required",
        "is_active",
    )

    search_fields = (
        "question",
        "indicator__code",
        "indicator__name",
    )

    ordering = (
        "indicator",
        "question_order",
    )