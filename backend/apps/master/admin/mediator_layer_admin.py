from django.contrib import admin

from apps.master.models import MediatorLayer


@admin.register(MediatorLayer)
class MediatorLayerAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "name",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    ordering = (
        "number",
    )
