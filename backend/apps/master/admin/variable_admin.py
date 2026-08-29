from django.contrib import admin

from apps.master.models import Variable


@admin.register(Variable)
class VariableAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "role",
        "order",
        "mediator_layer",
        "weight",
        "is_active",
    )

    list_filter = (
        "role",
        "mediator_layer",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )

    ordering = (
        "role",
        "mediator_layer",
        "order",
    )

    # code di-generate otomatis, tidak boleh diedit manual.
    readonly_fields = (
        "code",
    )
