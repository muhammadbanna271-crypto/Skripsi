from django.contrib import admin

from apps.analytics.models import (
    IndicatorScore,
    VariableScore,
    VillageScore,
)


admin.site.register(
    IndicatorScore,
)

admin.site.register(
    VariableScore,
)

admin.site.register(
    VillageScore,
)