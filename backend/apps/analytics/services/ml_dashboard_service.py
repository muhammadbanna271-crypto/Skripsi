from sklearn.decomposition import PCA

from apps.analytics.selectors.analytics_selector import AnalyticsSelector
from apps.master.models import Cluster, Village
from apps.respondent.models import Respondent
from apps.response.models import Response


CLUSTER_COLORS = [
    "#0d6efd",
    "#198754",
    "#dc3545",
    "#fd7e14",
    "#6f42c1",
]


class MLDashboardService:

    # =========================================================
    # RINGKASAN ATAS
    # =========================================================

    @staticmethod
    def summary():

        from apps.analytics.services.clustering_service import (
            ClusteringService,
        )

        registry = ClusteringService.ensure_trained()

        return {

            "total_village": Village.objects.count(),

            "total_respondent": Respondent.objects.count(),

            "total_response": Response.objects.count(),

            "is_trained": registry is not None,

            "trained_at": registry.created_at if registry else None,

            "n_clusters": registry.n_clusters if registry else 0,

            "silhouette_score": (
                registry.silhouette_score if registry else None
            ),

        }

    # =========================================================
    # PIE CHART -- distribusi jumlah desa per cluster
    # =========================================================

    @staticmethod
    def cluster_distribution():

        clusters = (
            Cluster.objects
            .filter(villages__isnull=False)
            .distinct()
        )

        result = []

        for index, cluster in enumerate(clusters):

            result.append({

                "label": cluster.name,

                "count": cluster.villages.count(),

                "color": (
                    cluster.color
                    or CLUSTER_COLORS[index % len(CLUSTER_COLORS)]
                ),

            })

        return result

    # =========================================================
    # SCATTER PLOT -- proyeksi 2D (PCA) dari feature matrix
    # =========================================================

    @staticmethod
    def scatter_data():

        villages, indicators, matrix = (
            AnalyticsSelector.feature_matrix()
        )

        if len(villages) < 2:
            return []

        pca = PCA(n_components=2)

        coordinates = pca.fit_transform(matrix)

        result = []

        for village, (x, y) in zip(villages, coordinates):

            cluster = village.cluster

            result.append({

                "village": village.name,

                "x": round(float(x), 3),

                "y": round(float(y), 3),

                "cluster": cluster.name if cluster else "Belum Dikluster",

                "color": (
                    cluster.color
                    if cluster and cluster.color
                    else "#6c757d"
                ),

            })

        return result

    # =========================================================
    # TABEL desa + cluster-nya
    # =========================================================

    @staticmethod
    def village_table():

        villages = (
            Village.objects
            .select_related("cluster", "village_score")
            .order_by("-village_score__total_score")
        )

        result = []

        for village in villages:

            score = getattr(village, "village_score", None)

            result.append({

                "village": village,

                "cluster": village.cluster,

                "total_score": score.total_score if score else 0,

                "rank": score.rank if score else "-",

            })

        return result

    # =========================================================
    # KESIMPULAN OTOMATIS
    # =========================================================

    @staticmethod
    def narrative_summary(variable_importance):

        from apps.analytics.services.clustering_service import (
            ClusteringService,
        )

        registry = ClusteringService.ensure_trained()

        if registry is None:

            return (
                "Model clustering belum pernah dijalankan. "
                "Klik tombol \"Retrain Model\" untuk memulai analisis."
            )

        total_village = Village.objects.count()

        top_variable = (
            variable_importance[0]
            if variable_importance
            else None
        )

        cluster_names = [
            info["name"]
            for info in registry.cluster_mapping.values()
        ]

        text = (
            f"Berdasarkan data historis dari {total_village} desa, "
            f"model K-Means berhasil membentuk {registry.n_clusters} "
            f"cluster ({', '.join(cluster_names)}) dengan silhouette "
            f"score {registry.silhouette_score:.3f}"
            if registry.silhouette_score is not None
            else f"Berdasarkan data historis dari {total_village} desa, "
            f"model K-Means berhasil membentuk {registry.n_clusters} "
            f"cluster ({', '.join(cluster_names)})"
        )

        if top_variable:

            text += (
                f". Indikator paling dominan dalam membedakan "
                f"karakteristik antar desa adalah variabel "
                f"\"{top_variable['name']}\" dengan kontribusi "
                f"sebesar {top_variable['percentage']}% terhadap "
                f"perbedaan cluster."
            )

        else:

            text += "."

        return text
