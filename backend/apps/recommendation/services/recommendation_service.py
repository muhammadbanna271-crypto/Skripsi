"""
Replace SELURUH isi apps/recommendation/services/recommendation_service.py
dengan file ini (lengkap, tidak perlu digabung manual lagi).
"""

from apps.recommendation.models import RecommendationResult
from apps.recommendation.selectors.recommendation_selector import (
    RecommendationSelector,
)

from apps.recommendation.services.topsis import (
    TOPSIS,
)


class RecommendationService:

    @staticmethod
    def _classify(score):
        """
        Klasifikasi skor preferensi TOPSIS (0-1) jadi status,
        warna badge, dan rekomendasi singkat.
        """

        if score >= 0.7:

            return {

                "status": "Sangat Layak",

                "badge": "success",

                "recommendation": (
                    "Prioritas utama untuk pengembangan desa wisata."
                ),

            }

        if score >= 0.5:

            return {

                "status": "Layak",

                "badge": "primary",

                "recommendation": (
                    "Layak dikembangkan lebih lanjut dengan "
                    "penguatan pada indikator yang masih rendah."
                ),

            }

        if score >= 0.3:

            return {

                "status": "Cukup Layak",

                "badge": "warning",

                "recommendation": (
                    "Perlu perbaikan pada beberapa indikator "
                    "sebelum diprioritaskan."
                ),

            }

        return {

            "status": "Kurang Layak",

            "badge": "danger",

            "recommendation": (
                "Membutuhkan pembenahan signifikan pada "
                "infrastruktur, fasilitas, dan pelayanan."
            ),

        }

    @classmethod
    def _run_topsis(cls):

        villages, indicators, matrix = (
            RecommendationSelector.decision_matrix()
        )

        if not villages:
            return None

        if not indicators:
            return None

        if matrix is None:
            return None

        if len(matrix) == 0:
            return None

        weights = [
            float(ind.weight)
            for ind in indicators
        ]

        criteria = [
            ind.criterion_type
            for ind in indicators
        ]

        topsis = TOPSIS(
            matrix,
            weights,
            criteria,
        )

        result = topsis.rank()

        ranking = []

        for village, score in zip(
            villages,
            result["preference"],
        ):

            score_value = float(score)

            classification = cls._classify(score_value)

            ranking.append(
                {
                    "village": village,
                    "score": score_value,
                    "status": classification["status"],
                    "badge": classification["badge"],
                    "recommendation": classification["recommendation"],
                }
            )

        ranking.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        return {
            "villages": villages,
            "indicators": indicators,
            "matrix": matrix,
            "ranking": ranking,
            "normalized": result["normalized"],
            "weighted": result["weighted"],
            "positive": result["positive"],
            "negative": result["negative"],
            "distance_positive": result["distance_positive"],
            "distance_negative": result["distance_negative"],
            "preference": result["preference"],
        }

    @classmethod
    def generate(cls):

        data = cls._run_topsis()

        if data is None:
            return []

        return data["ranking"]

    # =========================================================
    # CACHING -- recalculate() menghitung ulang (berat, manual
    # trigger saja), dashboard() cuma baca cache (ringan).
    # =========================================================

    @classmethod
    def recalculate(cls):
        """
        Ini yang MENGHITUNG ULANG (berat). Cuma dipanggil kalau
        ada yang klik tombol "Hitung Ulang" (superuser only) --
        BUKAN tiap kali dashboard dibuka.
        """

        data = cls._run_topsis()

        if data is None:
            ranking_json = []
            n_villages = 0
        else:
            ranking_json = [
                {
                    "village_id": item["village"].id,
                    "village_name": item["village"].name,
                    "score": item["score"],
                    "status": item["status"],
                    "badge": item["badge"],
                    "recommendation": item["recommendation"],
                }
                for item in data["ranking"]
            ]
            n_villages = len(data["ranking"])

        # Simpan sebagai 1 baris cache terbaru (replace yang lama)
        RecommendationResult.objects.all().delete()
        RecommendationResult.objects.create(
            ranking=ranking_json,
            n_villages=n_villages,
        )

        # Hasil sudah dihitung ulang -> simpan signature konfigurasi.
        from apps.analytics.models import AnalysisState

        AnalysisState.mark_computed()

        return ranking_json

    @classmethod
    def dashboard(cls):
        """
        Ini yang DIBACA tiap kali dashboard dibuka (ringan --
        cuma ambil dari cache, tanpa hitung TOPSIS ulang).
        Kalau cache belum ada (fresh deploy / konfigurasi berubah),
        hitung live dulu supaya dashboard & chatbot tetap jalan.
        """

        cached = RecommendationResult.objects.order_by(
            "-computed_at"
        ).first()

        if cached is None:
            cls.recalculate()
            cached = RecommendationResult.objects.order_by(
                "-computed_at"
            ).first()

        # FIXED: indicators tetap diambil live -- ini query
        # ringan (bukan bagian yang berat), tidak perlu di-cache.
        # Template butuh ini buat tabel "Indicator Weight".
        indicators = list(RecommendationSelector.indicators())

        if cached is None:
            return {
                "ranking": [],
                "result": [],
                "indicators": indicators,
                "computed_at": None,
                "has_cache": False,
            }

        return {
            "ranking": cached.ranking,
            "result": cached.ranking,
            "indicators": indicators,
            "computed_at": cached.computed_at,
            "has_cache": True,
        }