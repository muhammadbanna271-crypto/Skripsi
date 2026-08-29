from django.contrib import admin

from apps.master.models import District

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "code",
        "name",
    )

    ordering = (
        "name",
    )