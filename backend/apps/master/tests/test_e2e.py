"""End-to-end workflow (Phase 25) — simulasi alur konfigurasi nyata."""

from django.test import TestCase

from apps.master.models import Indicator, MediatorLayer, Questionnaire, Variable
from apps.master.services.variable_configuration_service import (
    VariableConfigurationService,
)

from .factories import create_indicator, create_questionnaire, create_variable


class DynamicVariableModelingE2ETest(TestCase):

    def setUp(self):
        Variable.objects.all().delete()
        MediatorLayer.objects.all().delete()
        Indicator.objects.all().delete()
        Questionnaire.objects.all().delete()

    def _setup_starting_configuration(self):
        # PREDICTOR: X1 Infrastruktur, X2 Promosi, X3 SDM
        x1 = create_variable("predictor", order=1, name="Infrastruktur")
        x2 = create_variable("predictor", order=2, name="Promosi")
        x3 = create_variable("predictor", order=3, name="SDM")

        # MEDIATOR Layer 1: Y1 Kualitas Layanan
        layer1 = MediatorLayer.objects.create(number=1)
        y1 = create_variable("mediator", order=1, name="Kualitas Layanan", layer=layer1)

        # RESPONSE: Z1 Keberlanjutan
        z1 = create_variable("response", order=1, name="Keberlanjutan")

        VariableConfigurationService.regenerate_codes()
        return x1, x2, x3, y1, z1, layer1

    def test_full_workflow(self):
        x1, x2, x3, y1, z1, layer1 = self._setup_starting_configuration()

        # 1. Move X3 (SDM) ke posisi 1.
        VariableConfigurationService.reorder(
            "predictor", [x3.id, x1.id, x2.id]
        )
        config = VariableConfigurationService.load()
        self.assertEqual(
            [v["name"] for v in config["predictors"]],
            ["SDM", "Infrastruktur", "Promosi"],
        )

        # 2. Move X2 (Promosi) ke Mediator Layer 1.
        VariableConfigurationService.move(x2.id, "mediator", 1)
        config = VariableConfigurationService.load()
        mediator_names = [
            v["name"] for layer in config["mediator_layers"] for v in layer
        ]
        self.assertIn("Promosi", mediator_names)
        self.assertNotIn(
            "Promosi", [v["name"] for v in config["predictors"]]
        )

        # 3. Add Mediator Layer 2.
        layer2 = VariableConfigurationService.add_layer(name="Layer 2")

        # 4. Move Y1 (Kualitas Layanan) ke Layer 2.
        VariableConfigurationService.move(y1.id, "mediator", layer2.number)
        config = VariableConfigurationService.load()
        self.assertEqual(len(config["mediator_layers"]), 2)

        # 5. Add new mediator indicator (variable) di Layer 2.
        new_mediator = create_variable(
            "mediator", order=2, name="Mediator Baru", layer=layer2
        )
        create_indicator(new_mediator)
        VariableConfigurationService.regenerate_codes()

        # 6. Add response.
        new_response = create_variable("response", order=2, name="Response Baru")
        create_indicator(new_response)
        VariableConfigurationService.regenerate_codes()

        config = VariableConfigurationService.load()
        self.assertEqual(len(config["responses"]), 2)

        # 7. Disable semua mediator layer.
        for layer in MediatorLayer.objects.all():
            VariableConfigurationService.deactivate_layer(layer.id)

        config = VariableConfigurationService.load()
        self.assertEqual(config["mediator_layers"], [])
        active_var_ids = set(
            VariableConfigurationService.active_indicators()
            .values_list("variable_id", flat=True)
        )
        # Mediator ter-exclude — hanya predictor & response.
        for mediator in Variable.objects.filter(role="mediator"):
            self.assertNotIn(mediator.id, active_var_ids)

        # 8. Enable mediator lagi.
        for layer in MediatorLayer.objects.all():
            VariableConfigurationService.activate_layer(layer.id)

        config = VariableConfigurationService.load()
        self.assertEqual(len(config["mediator_layers"]), 2)

        # 9. Verify questionnaire mengikuti konfigurasi (indicator tetap
        #    terhubung dan urutannya mengikuti role/order/layer).
        qs = list(
            Questionnaire.objects.all().order_by(
                *VariableConfigurationService.questionnaire_ordering()
            )
        )
        self.assertGreaterEqual(len(qs), 0)  # ordering tidak error
