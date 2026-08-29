"""
Replace isi apps/recommendation/views/recommendation_views.py
dengan ini. Tambahin juga path baru di urls.py (contoh di bawah).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect

from common.models.decorators import staff_required

from apps.analytics.models import AnalysisState
from apps.recommendation.services import RecommendationService


@staff_required
def recommendation_dashboard(request):
    """
    Hanya staff/superuser — dashboard ranking/TOPSIS adalah data riset
    internal, bukan untuk visitor umum.
    """

    context = RecommendationService.dashboard()

    context["can_recalculate"] = True

    # Penanda apakah ada perubahan konfigurasi yang belum dihitung ulang.
    context["analysis_stale"] = AnalysisState.is_stale()

    return render(
        request,
        "recommendation/dashboard.html",
        context,
    )


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def recalculate_recommendation(request):
    """
    Cuma superuser yang bisa trigger hitung ulang. Kalau visitor
    atau user biasa coba akses URL ini langsung, otomatis di-
    redirect ke halaman login (login_required) atau ditolak
    (user_passes_test) sebelum masuk ke sini sama sekali.
    """

    if request.method == "POST":

        RecommendationService.recalculate()

        messages.success(
            request,
            "Hasil rekomendasi berhasil dihitung ulang.",
        )

    return redirect("recommendation:dashboard")


# --------------------------------------------------------------
# Tambahan di apps/recommendation/urls/recommendation_urls.py:
#
# from apps.recommendation.views.recommendation_views import (
#     recommendation_dashboard,
#     recalculate_recommendation,
# )
#
# urlpatterns = [
#     path("", recommendation_dashboard, name="dashboard"),
#     path(
#         "recalculate/",
#         recalculate_recommendation,
#         name="recalculate",
#     ),
#     ...
# ]
# --------------------------------------------------------------