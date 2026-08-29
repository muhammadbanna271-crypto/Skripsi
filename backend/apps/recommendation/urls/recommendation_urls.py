from django.urls import path

from apps.recommendation.views.recommendation_views import (
    recommendation_dashboard,
    recalculate_recommendation,
)
from apps.recommendation.views.export_views import (
    export_excel,
    export_pdf,
)

app_name = "recommendation"

urlpatterns = [
    path("", recommendation_dashboard, name="dashboard"),
    path("recalculate/", recalculate_recommendation, name="recalculate"),
    path("export/excel/", export_excel, name="export-excel"),
    path("export/pdf/", export_pdf, name="export-pdf"),
]