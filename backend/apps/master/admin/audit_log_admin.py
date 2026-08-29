from django.contrib import admin

from apps.master.models import VariableConfigAuditLog


@admin.register(VariableConfigAuditLog)
class VariableConfigAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "action",
        "variable",
        "old_role",
        "new_role",
        "old_order",
        "new_order",
    )

    list_filter = (
        "action",
        "old_role",
        "new_role",
    )

    search_fields = (
        "variable__name",
        "variable__code",
        "user__username",
    )

    readonly_fields = (
        "user",
        "action",
        "variable",
        "old_role",
        "new_role",
        "old_order",
        "new_order",
        "old_layer",
        "new_layer",
        "detail",
        "created_at",
    )

    def has_add_permission(self, request):
        return False
