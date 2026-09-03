from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from common.models.decorators import staff_required

from apps.analytics.services import AnalyticsService

from apps.analytics.models import AnalysisState

from apps.master.models import Village
from apps.survey.models import Survey
from apps.respondent.models import Respondent
from apps.response.models import Response


@staff_required
def analytics_dashboard(request):

    context = {

        "total_village": Village.objects.count(),

        "total_survey": Survey.objects.count(),

        "total_respondent": Respondent.objects.count(),

        "total_response": Response.objects.count(),

        "average_score": AnalyticsService.average_score(),

        "village_scores": AnalyticsService.village_scores(),

        "likert_distribution": AnalyticsService.likert_distribution(),

        "indicator_scores": AnalyticsService.indicator_scores(),
    }

    return render(

        request,

        "analytics/dashboard.html",

        context,

    )


# =============================================================
# ML DASHBOARD (clustering, feature importance, TOPSIS,
# radar chart, export) -- terpisah dari dashboard lama di atas.
# =============================================================

@staff_required
def ml_dashboard(request):

    from apps.analytics.services.cluster_recommendation_service import (
        ClusterRecommendationService,
    )
    from apps.analytics.services.feature_importance_service import (
        FeatureImportanceService,
    )
    from apps.analytics.services.ml_dashboard_service import (
        MLDashboardService,
    )
    from apps.analytics.services.relationship_analysis_service import (
        RelationshipAnalysisService,
    )
    from apps.survey_analysis.services.dashboard import (
        SurveyAnalysisDashboard,
    )

    village_table = MLDashboardService.village_table()

    survey = SurveyAnalysisDashboard.context()

    variable_importance = (
        FeatureImportanceService.dominant_variables()
    )

    context = {

        "summary": MLDashboardService.summary(),

        "cluster_distribution": (
            MLDashboardService.cluster_distribution()
        ),

        "scatter_data": MLDashboardService.scatter_data(),

        "village_table": village_table,

        "villages": Village.objects.all().order_by("name"),

        "variable_importance": variable_importance,

        "dominant_indicators": (
            FeatureImportanceService.dominant_indicators()
        ),

        "cluster_ranking": (
            ClusterRecommendationService.rank_within_clusters()
        ),

        "narrative": MLDashboardService.narrative_summary(
            variable_importance,
        ),

        "relationship": RelationshipAnalysisService.run(),

        "analysis_stale": AnalysisState.is_stale(),

        "survey": survey,

    }

    return render(

        request,

        "analytics/ml_dashboard.html",

        context,

    )


@staff_required
def run_survey_pipeline(request):

    from apps.survey_analysis.services.dashboard import (
        SurveyAnalysisDashboard,
    )

    if request.method == "POST":

        out = SurveyAnalysisDashboard.run()

        state = out.get("state")

        if state is not None and getattr(state, "status", None) == "STOPPED":

            stop_msg = ""

            for h in reversed(state.history):
                if h.get("status") == "STOPPED" and h.get("message"):
                    stop_msg = h["message"]
                    break

            messages.warning(
                request,
                (
                    "Pipeline SEM/LCA/SHAP berhenti: "
                    f"{stop_msg or 'lihat log pipeline.'}"
                ),
            )

        else:

            messages.success(
                request,
                "Pipeline SEM/LCA/SHAP selesai dijalankan.",
            )

    return redirect("analytics:ml-dashboard")


@staff_required
def retrain_model(request):

    from apps.analytics.services.clustering_service import (
        ClusteringService,
    )

    if request.method == "POST":

        result = ClusteringService.train_and_save()

        if result["success"]:

            messages.success(
                request,
                (
                    "Model berhasil di-training ulang atas "
                    f"{result['n_villages']} desa."
                ),
            )

        else:

            messages.error(
                request,
                result["message"],
            )

    return redirect("analytics:ml-dashboard")


@staff_required
def predict_village(request, village_id):

    from apps.analytics.services.clustering_service import (
        ClusteringService,
    )

    village = get_object_or_404(Village, pk=village_id)

    if request.method == "POST":

        result = ClusteringService.predict_village(village)

        if result["success"]:

            messages.success(
                request,
                (
                    f"Desa \"{village.name}\" diprediksi masuk "
                    f"cluster \"{result['cluster']['name']}\"."
                ),
            )

        else:

            messages.error(
                request,
                result["message"],
            )

    return redirect("analytics:ml-dashboard")


@staff_required
def village_radar_json(request, village_id):

    from apps.analytics.services.feature_importance_service import (
        FeatureImportanceService,
    )

    village = get_object_or_404(Village, pk=village_id)

    radar = FeatureImportanceService.radar_axes_for_village(
        village,
    )

    return JsonResponse({

        "village": village.name,

        "labels": [axis["code"] for axis in radar],

        "values": [axis["score"] for axis in radar],

    })


@staff_required
def relationship_json(request):
    """JSON korelasi predictor -> response (config-driven)."""

    from apps.analytics.services.relationship_analysis_service import (
        RelationshipAnalysisService,
    )

    return JsonResponse({
        "relationships": RelationshipAnalysisService.run(),
    })


@staff_required
def simulate_cluster(request):

    from apps.master.models import Variable

    from apps.analytics.services.clustering_service import (
        ClusteringService,
    )

    variables = (
        Variable.objects
        .filter(is_active=True)
        .order_by("code")
    )

    result = None

    submitted_scores = {}

    if request.method == "POST":

        variable_scores = {}

        for variable in variables:

            raw_value = request.POST.get(
                f"variable_{variable.code}",
                3,
            )

            value = float(raw_value)

            variable_scores[variable.code] = value

            submitted_scores[variable.code] = value

        result = ClusteringService.predict_manual(
            variable_scores,
        )

        if not result["success"]:

            messages.error(request, result["message"])

    context = {

        "variables": variables,

        "result": result,

        "submitted_scores": submitted_scores,

    }

    return render(

        request,

        "analytics/simulate.html",

        context,

    )


@staff_required
def export_excel(request):

    from apps.analytics.exports.excel_export import (
        AnalyticsExcelExport,
    )
    from apps.analytics.services.export_data_service import (
        ExportDataService,
    )

    data = ExportDataService.compile()

    return AnalyticsExcelExport.export(data)


@staff_required
def export_pdf(request):

    from apps.analytics.exports.pdf_export import (
        AnalyticsPDFExport,
    )
    from apps.analytics.services.export_data_service import (
        ExportDataService,
    )

    data = ExportDataService.compile()

    return AnalyticsPDFExport.export(data)