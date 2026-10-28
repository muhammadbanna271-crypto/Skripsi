from django.urls import path

from apps.master.views.import_views import (
    DistrictImportTemplateView,
    DistrictImportView,
    VariableImportTemplateView,
    VariableImportView,
    VillageImportTemplateView,
    VillageImportView,
)

urlpatterns = [

    path(
        "district/import/",
        DistrictImportView.as_view(),
        name="district-import",
    ),

    path(
        "district/import/template/",
        DistrictImportTemplateView.as_view(),
        name="district-import-template",
    ),

    path(
        "village/import/",
        VillageImportView.as_view(),
        name="village-import",
    ),

    path(
        "village/import/template/",
        VillageImportTemplateView.as_view(),
        name="village-import-template",
    ),

    path(
        "variable/import/",
        VariableImportView.as_view(),
        name="variable-import",
    ),

    path(
        "variable/import/template/",
        VariableImportTemplateView.as_view(),
        name="variable-import-template",
    ),

]
