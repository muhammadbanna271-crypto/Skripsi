from django.contrib import admin

from apps.master.models import Cluster

@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "color",
        "created_at",
    )

    search_fields = (
        "code",
        "name",
    )

    ordering = (
        "code",
    )