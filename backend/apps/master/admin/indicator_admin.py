from django.contrib import admin

from apps.master.models import Indicator

@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "variable",
        "weight",
        "is_active",
    )

    list_filter = (
        "variable",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )

    ordering = (
        "code",
    )