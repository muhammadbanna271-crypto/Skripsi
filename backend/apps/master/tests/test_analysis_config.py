from django.test import TestCase

from apps.master.models import Indicator, MediatorLayer, Variable
from apps.master.services.variable_configuration_service import (
    VariableConfigurationService,
)

from .factories import create_indicator, create_variable


class AnalysisConfigTest(TestCase):

    def setUp(self):
        Variable.objects.all().delete()
        MediatorLayer.objects.all().delete()
        Indicator.objects.all().delete()

    def test_zero_mediator(self):
        p = create_variable("predictor", order=1, name="P")
        r = create_variable("response", order=1, name="R")
        create_indicator(p)
        create_indicator(r)

        config = VariableConfigurationService.load()
        self.assertEqual(config["mediator_layers"], [])
        self.assertEqual(
            VariableConfigurationService.active_indicators().count(), 2
        )

    def test_n_mediator_layers(self):
        p = create_variable("predictor", order=1, name="P")
        r = create_variable("response", order=1, name="R")
        create_indicator(p)
        create_indicator(r)

        layer1 = MediatorLayer.objects.create(number=1)
        layer2 = MediatorLayer.objects.create(number=2)
        layer3 = MediatorLayer.objects.create(number=3)
        m1 = create_variable("mediator", order=1, name="M1", layer=layer1)
        m2 = create_variable("mediator", order=1, name="M2", layer=layer2)
        m3 = create_variable("mediator", order=1, name="M3", layer=layer3)
        create_indicator(m1)
        create_indicator(m2)
        create_indicator(m3)

        VariableConfigurationService.regenerate_codes()

        config = VariableConfigurationService.load()
        self.assertEqual(len(config["mediator_layers"]), 3)
        self.assertEqual(
            VariableConfigurationService.active_indicators().count(), 5
        )

    def test_disable_mediator_layer_excludes_indicators(self):
        p = create_variable("predictor", order=1, name="P")
        r = create_variable("response", order=1, name="R")
        create_indicator(p)
        create_indicator(r)

        layer1 = MediatorLayer.objects.create(number=1)
        m1 = create_variable("mediator", order=1, name="M1", layer=layer1)
        create_indicator(m1)

        self.assertEqual(
            VariableConfigurationService.active_indicators().count(), 3
        )

        VariableConfigurationService.deactivate_layer(layer1.id)

        self.assertEqual(
            VariableConfigurationService.active_indicators().count(), 2
        )
        self.assertEqual(
            VariableConfigurationService.load()["mediator_layers"], []
        )

    def test_inactive_variable_is_excluded(self):
        p = create_variable("predictor", order=1, name="P")
        inactive = create_variable(
            "predictor", order=2, name="P2", is_active=False
        )
        create_indicator(p)
        create_indicator(inactive)

        active_ids = list(
            VariableConfigurationService.active_indicators()
            .values_list("variable_id", flat=True)
        )
        self.assertIn(p.id, active_ids)
        self.assertNotIn(inactive.id, active_ids)
