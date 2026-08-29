from django.contrib import admin

from apps.master.models import Village


@admin.register(Village)
class VillageAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "district",
        "cluster",
        "is_active",
        "created_at",
    )

    search_fields = (
        "code",
        "name",
        "district__name",
    )

    list_filter = (
        "district",
        "cluster",
        "is_active",
    )

    ordering = (
        "code",
    )