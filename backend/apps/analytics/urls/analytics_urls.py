from django.urls import path

from apps.analytics.views import (
    analytics_dashboard,
    ml_dashboard,
    retrain_model,
    predict_village,
    village_radar_json,
    relationship_json,
    simulate_cluster,
    export_excel,
    export_pdf,
)


urlpatterns = [

    path(

        "",

        analytics_dashboard,

        name="dashboard",

    ),

    path(
        "ml/",
        ml_dashboard,
        name="ml-dashboard",
    ),

    path(
        "ml/retrain/",
        retrain_model,
        name="ml-retrain",
    ),

    path(
        "ml/predict/<int:village_id>/",
        predict_village,
        name="ml-predict",
    ),

    path(
        "ml/radar/<int:village_id>/",
        village_radar_json,
        name="ml-radar-json",
    ),

    path(
        "ml/relationship/",
        relationship_json,
        name="ml-relationship-json",
    ),

    path(
        "ml/simulate/",
        simulate_cluster,
        name="ml-simulate",
    ),

    path(
        "ml/export/excel/",
        export_excel,
        name="ml-export-excel",
    ),

    path(
        "ml/export/pdf/",
        export_pdf,
        name="ml-export-pdf",
    ),

]