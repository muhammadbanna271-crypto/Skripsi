from django.urls import path

from apps.slr.views import create_run, dashboard

urlpatterns = [path("", dashboard, name="dashboard"), path("runs/create/", create_run, name="create-run")]
