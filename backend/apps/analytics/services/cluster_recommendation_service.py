from apps.recommendation.selectors.recommendation_selector import (
    RecommendationSelector,
)
from apps.recommendation.services.topsis import TOPSIS


class ClusterRecommendationService:
    """
    Menjalankan TOPSIS SETELAH cluster terbentuk -- ranking desa
    dilakukan di dalam masing-masing cluster (bukan lintas cluster),
    supaya prioritas rekomendasi adil dibandingkan sesama
    "levelnya".
    """

    @classmethod
    def rank_within_clusters(cls):

        villages, indicators, matrix = (
            RecommendationSelector.decision_matrix()
        )

        if not villages:
            return []

        weights = [
            float(indicator.weight) for indicator in indicators
        ]

        criteria = [
            indicator.criterion_type for indicator in indicators
        ]

        groups = {}

        for village, row in zip(villages, matrix):

            cluster = village.cluster

            key = cluster.id if cluster else 0

            bucket = groups.setdefault(
                key,
                {
                    "cluster": cluster,
                    "villages": [],
                    "rows": [],
                },
            )

            bucket["villages"].append(village)

            bucket["rows"].append(row)

        result = []

        for bucket in groups.values():

            if len(bucket["rows"]) < 2:

                # TOPSIS butuh minimal 2 alternatif untuk dibandingkan
                ranking = [

                    {
                        "village": village,
                        "score": None,
                        "rank": 1,
                    }

                    for village in bucket["villages"]

                ]

            else:

                topsis = TOPSIS(
                    bucket["rows"],
                    weights,
                    criteria,
                )

                topsis_result = topsis.rank()

                pairs = list(
                    zip(
                        bucket["villages"],
                        topsis_result["preference"],
                    )
                )

                pairs.sort(
                    key=lambda pair: pair[1],
                    reverse=True,
                )

                ranking = [

                    {
                        "village": village,
                        "score": float(score),
                        "rank": rank,
                    }

                    for rank, (village, score) in enumerate(
                        pairs,
                        start=1,
                    )

                ]

            result.append({

                "cluster": bucket["cluster"],

                "ranking": ranking,

            })

        result.sort(
            key=lambda item: (
                item["cluster"].name if item["cluster"] else "zzz"
            )
        )

        return result
