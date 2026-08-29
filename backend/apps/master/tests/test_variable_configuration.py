from django.test import TestCase

from apps.master.models import Indicator, MediatorLayer, Questionnaire, Variable
from apps.master.services.variable_configuration_service import (
    ConfigurationError,
    VariableConfigurationService,
)

from .factories import (
    create_indicator,
    create_questionnaire,
    create_variable,
)


class VariableConfigurationServiceTest(TestCase):

    def setUp(self):
        Variable.objects.all().delete()
        MediatorLayer.objects.all().delete()
        Indicator.objects.all().delete()
        Questionnaire.objects.all().delete()

    def test_role_grouping_and_generated_codes(self):
        layer1 = MediatorLayer.objects.create(number=1)
        create_variable("predictor", order=1, name="P1")
        create_variable("predictor", order=2, name="P2")
        create_variable("mediator", order=1, name="M1", layer=layer1)
        create_variable("response", order=1, name="R1")

        VariableConfigurationService.regenerate_codes()

        config = VariableConfigurationService.load()
        self.assertEqual(
            [v["code"] for v in config["predictors"]], ["X1", "X2"]
        )
        self.assertEqual(
            [[v["code"] for v in layer] for layer in config["mediator_layers"]],
            [["Y1"]],
        )
        self.assertEqual([v["code"] for v in config["responses"]], ["Z1"])

    def test_reorder_predictor_is_persistent(self):
        p1 = create_variable("predictor", order=1, name="A")
        p2 = create_variable("predictor", order=2, name="B")
        p3 = create_variable("predictor", order=3, name="C")
        VariableConfigurationService.regenerate_codes()

        # Pindahkan C ke posisi pertama.
        VariableConfigurationService.reorder(
            "predictor", [p3.id, p1.id, p2.id]
        )

        config = VariableConfigurationService.load()
        names = [v["name"] for v in config["predictors"]]
        codes = [v["code"] for v in config["predictors"]]

        self.assertEqual(names, ["C", "A", "B"])
        self.assertEqual(codes, ["X1", "X2", "X3"])

        # id internal tetap sama (tidak berubah).
        self.assertEqual(
            {v["id"] for v in config["predictors"]}, {p1.id, p2.id, p3.id}
        )

    def test_move_between_groups_keeps_questionnaire_relationship(self):
        layer1 = MediatorLayer.objects.create(number=1)
        var = create_variable("predictor", order=1, name="P1")
        ind = create_indicator(var, code="P1.1", name="Ind1")
        q = create_questionnaire(ind)
        VariableConfigurationService.regenerate_codes()

        VariableConfigurationService.move(var.id, "mediator", 1)

        var.refresh_from_db()
        self.assertEqual(var.role, "mediator")
        self.assertEqual(var.mediator_layer.number, 1)

        # Questionnaire tetap terhubung ke indikator yang sama.
        self.assertTrue(
            Questionnaire.objects.filter(pk=q.pk, indicator=ind).exists()
        )
        # Indicator tetap terhubung ke variable yang sama.
        self.assertTrue(
            Indicator.objects.filter(pk=ind.pk, variable=var).exists()
        )

    def test_move_with_position_shifts_down(self):
        layer1 = MediatorLayer.objects.create(number=1)
        create_variable("mediator", order=1, name="M1", layer=layer1)
        create_variable("mediator", order=2, name="M2", layer=layer1)
        r = create_variable("response", order=1, name="R1")
        VariableConfigurationService.regenerate_codes()

        # Sisipkan R1 ke mediator posisi 1 -> M1 & M2 geser ke bawah.
        VariableConfigurationService.move(r.id, "mediator", 1, position=1)

        config = VariableConfigurationService.load()
        mediator_names = [
            v["name"]
            for layer in config["mediator_layers"]
            for v in layer
        ]
        self.assertEqual(mediator_names, ["R1", "M1", "M2"])

    def test_add_deactivate_activate_remove_layer(self):
        layer = MediatorLayer.objects.create(number=1)

        VariableConfigurationService.deactivate_layer(layer.id)
        layer.refresh_from_db()
        self.assertFalse(layer.is_active)

        VariableConfigurationService.activate_layer(layer.id)
        layer.refresh_from_db()
        self.assertTrue(layer.is_active)

        layer2 = VariableConfigurationService.add_layer(name="Layer 2")
        self.assertEqual(layer2.number, 2)

        VariableConfigurationService.remove_layer(layer2.id)
        self.assertFalse(MediatorLayer.objects.filter(pk=layer2.id).exists())

    def test_validation_duplicate_order(self):
        create_variable("predictor", order=1, name="A")
        create_variable("predictor", order=1, name="B")
        errors = VariableConfigurationService.validate_configuration()
        self.assertTrue(any("Duplicate order" in e for e in errors))

    def test_validation_empty_predictor(self):
        create_variable("response", order=1, name="R1")
        errors = VariableConfigurationService.validate_configuration()
        self.assertTrue(any("predictor" in e.lower() for e in errors))

    def test_validation_mediator_without_layer(self):
        create_variable("mediator", order=1, name="M1", layer=None)
        errors = VariableConfigurationService.validate_configuration()
        self.assertTrue(any("tidak punya layer" in e for e in errors))

    def test_invalid_role_move_raises(self):
        var = create_variable("predictor", order=1, name="A")
        with self.assertRaises(ConfigurationError):
            VariableConfigurationService.move(var.id, "invalid_role", None)

    def test_invalid_role_reorder_raises(self):
        with self.assertRaises(ConfigurationError):
            VariableConfigurationService.reorder("invalid_role", [])

    def test_group_variables_groups_by_role(self):
        layer1 = MediatorLayer.objects.create(number=1)
        p = create_variable("predictor", order=1, name="P")
        m = create_variable("mediator", order=1, name="M", layer=layer1)
        r = create_variable("response", order=1, name="R")

        grouped = VariableConfigurationService.group_variables([p, m, r])

        self.assertEqual([v.id for v in grouped["predictors"]], [p.id])
        self.assertEqual([v.id for v in grouped["responses"]], [r.id])
        self.assertEqual(len(grouped["mediator_layers"]), 1)
        self.assertEqual(
            grouped["mediator_layers"][0]["layer"].number, 1
        )
        self.assertEqual(
            [v.id for v in grouped["mediator_layers"][0]["variables"]],
            [m.id],
        )

    def test_group_variables_no_mediator(self):
        p = create_variable("predictor", order=1, name="P")
        r = create_variable("response", order=1, name="R")

        grouped = VariableConfigurationService.group_variables([p, r])

        self.assertEqual(grouped["mediator_layers"], [])

    def test_variable_buttons_follow_config_order(self):
        layer1 = MediatorLayer.objects.create(number=1)
        create_variable("predictor", order=1, name="P1")
        create_variable("predictor", order=2, name="P2")
        create_variable("mediator", order=1, name="M1", layer=layer1)
        create_variable("response", order=1, name="R1")
        VariableConfigurationService.regenerate_codes()

        codes = [
            b["code"]
            for b in VariableConfigurationService.variable_buttons()
        ]

        self.assertEqual(codes, ["X1", "X2", "Y1", "Z1"])

    def test_filter_by_group(self):
        layer1 = MediatorLayer.objects.create(number=1)
        layer2 = MediatorLayer.objects.create(number=2)
        p = create_variable("predictor", order=1, name="P")
        m1 = create_variable("mediator", order=1, name="M1", layer=layer1)
        m2 = create_variable("mediator", order=1, name="M2", layer=layer2)
        r = create_variable("response", order=1, name="R")

        qs = Variable.objects.all()
        ids = lambda queryset: set(
            queryset.values_list("id", flat=True)
        )

        self.assertEqual(
            ids(VariableConfigurationService.filter_by_group(qs, "")),
            {p.id, m1.id, m2.id, r.id},
        )
        self.assertEqual(
            ids(VariableConfigurationService.filter_by_group(qs, "predictor")),
            {p.id},
        )
        self.assertEqual(
            ids(VariableConfigurationService.filter_by_group(qs, "mediator-2")),
            {m2.id},
        )
        self.assertEqual(
            ids(VariableConfigurationService.filter_by_group(qs, "response")),
            {r.id},
        )

    def test_group_filter_options(self):
        MediatorLayer.objects.create(number=1)
        MediatorLayer.objects.create(number=2)

        options = VariableConfigurationService.group_filter_options()

        self.assertEqual(
            [o["value"] for o in options],
            ["", "predictor", "mediator-1", "mediator-2", "response"],
        )
