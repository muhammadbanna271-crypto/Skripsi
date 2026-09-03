from django.urls import path

from apps.survey_analysis.ui.views import dashboard

app_name = "survey_analysis"

urlpatterns = [
    path("", dashboard, name="dashboard"),
]
