import numpy as np
from django.test import SimpleTestCase

from apps.analytics.ml.clustering import KMeansClusterModel
from apps.analytics.ml.feature_importance import (
    aggregate_importance_by_group,
    compute_feature_importance,
)
from apps.recommendation.services.topsis import TOPSIS


class FeatureImportanceTest(SimpleTestCase):

    def test_compute_feature_importance(self):
        X = [[0, 0, 0], [0, 0, 0], [1, 1, 1], [1, 1, 1], [0, 0, 0]]
        labels = [0, 0, 1, 1, 0]
        names = ["a", "b", "c"]

        result = compute_feature_importance(X, labels, names)

        self.assertEqual(len(result), 3)
        self.assertEqual({r["feature"] for r in result}, {"a", "b", "c"})
        self.assertAlmostEqual(
            sum(r["importance"] for r in result), 1.0, places=2
        )
        # Terurut menurun.
        importances = [r["importance"] for r in result]
        self.assertEqual(importances, sorted(importances, reverse=True))

    def test_compute_feature_importance_single_class_returns_empty(self):
        X = [[0, 0], [1, 1], [2, 2]]
        labels = [0, 0, 0]
        result = compute_feature_importance(X, labels, ["a", "b"])
        self.assertEqual(result, [])

    def test_aggregate_importance_by_group(self):
        fi = [
            {"feature": "a", "importance": 0.5},
            {"feature": "b", "importance": 0.3},
            {"feature": "c", "importance": 0.2},
        ]
        mapping = {"a": "X1", "b": "X1", "c": "X2"}

        result = aggregate_importance_by_group(fi, mapping)

        by_group = {r["group"]: r["percentage"] for r in result}
        self.assertAlmostEqual(by_group["X1"], 80.0, places=1)
        self.assertAlmostEqual(by_group["X2"], 20.0, places=1)


class TOPSTest(SimpleTestCase):

    def test_rank_prefers_higher_benefit(self):
        matrix = [[1, 1, 1], [2, 2, 2], [3, 3, 3]]
        topsis = TOPSIS(matrix, [1, 1, 1], ["benefit", "benefit", "benefit"])

        prefs = list(topsis.rank()["preference"])

        self.assertEqual(len(prefs), 3)
        self.assertTrue(all(0 <= p <= 1 for p in prefs))
        self.assertLess(prefs[0], prefs[1])
        self.assertLess(prefs[1], prefs[2])

    def test_cost_criteria_prefers_lower(self):
        matrix = [[1], [2], [3]]
        topsis = TOPSIS(matrix, [1], ["cost"])

        prefs = list(topsis.rank()["preference"])

        # Nilai terendah (alternatif 1) paling diunggulkan.
        self.assertGreater(prefs[0], prefs[2])


class KMeansClusterModelTest(SimpleTestCase):

    def test_fit_two_clusters(self):
        X = np.array([[0, 0], [0.1, 0], [5, 5], [5.1, 5]])

        model = KMeansClusterModel(n_clusters=2, random_state=42)
        result = model.fit(X)

        self.assertEqual(len(result["labels"]), 4)
        self.assertEqual(len(set(result["labels"])), 2)
        self.assertIsNotNone(result["silhouette_score"])
        self.assertIsNotNone(result["inertia"])
