from django.test import TestCase

from apps.analytics.models import VariableScore
from apps.analytics.services.relationship_analysis_service import (
    RelationshipAnalysisService,
)
from apps.master.models import District, MediatorLayer, Variable, Village
from apps.master.services.variable_configuration_service import (
    VariableConfigurationService,
)
from apps.master.tests.factories import create_variable


class RelationshipAnalysisServiceTest(TestCase):

    def setUp(self):
        District.objects.all().delete()
        Village.objects.all().delete()
        Variable.objects.all().delete()
        MediatorLayer.objects.all().delete()
        VariableScore.objects.all().delete()

    def _make_villages(self, n=2):
        district = District.objects.create(code="D1", name="Dist 1")
        return [
            Village.objects.create(
                code=f"V{i}", name=f"Village {i}", district=district
            )
            for i in range(1, n + 1)
        ]

    def test_positive_correlation(self):
        v1, v2 = self._make_villages()

        p = create_variable("predictor", order=1, name="P")
        r = create_variable("response", order=1, name="R")
        VariableConfigurationService.regenerate_codes()

        VariableScore.objects.create(village=v1, variable=p, score=1)
        VariableScore.objects.create(village=v1, variable=r, score=1)
        VariableScore.objects.create(village=v2, variable=p, score=3)
        VariableScore.objects.create(village=v2, variable=r, score=3)

        result = RelationshipAnalysisService.run()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["predictor"], "X1")
        self.assertEqual(result[0]["response"], "Z1")
        self.assertAlmostEqual(result[0]["correlation"], 1.0, places=2)

    def test_negative_correlation(self):
        v1, v2 = self._make_villages()

        p = create_variable("predictor", order=1, name="P")
        r = create_variable("response", order=1, name="R")
        VariableConfigurationService.regenerate_codes()

        VariableScore.objects.create(village=v1, variable=p, score=1)
        VariableScore.objects.create(village=v1, variable=r, score=3)
        VariableScore.objects.create(village=v2, variable=p, score=3)
        VariableScore.objects.create(village=v2, variable=r, score=1)

        result = RelationshipAnalysisService.run()
        self.assertAlmostEqual(result[0]["correlation"], -1.0, places=2)

    def test_no_predictor_returns_empty(self):
        create_variable("response", order=1, name="R")
        self.assertEqual(RelationshipAnalysisService.run(), [])
