from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.master.models import (
    MediatorLayer,
    Variable,
    VariableConfigAuditLog,
)
from apps.master.services.variable_configuration_service import (
    VariableConfigurationService,
)

from .factories import create_variable


class VariableConfigAuditLogTest(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            "auditor", "a@example.com", "pass"
        )
        Variable.objects.all().delete()
        MediatorLayer.objects.all().delete()
        VariableConfigAuditLog.objects.all().delete()

    def test_move_records_audit(self):
        layer1 = MediatorLayer.objects.create(number=1)
        var = create_variable("predictor", order=1, name="P1")
        VariableConfigurationService.regenerate_codes()

        VariableConfigurationService.move(
            var.id, "mediator", 1, user=self.user
        )

        entry = VariableConfigAuditLog.objects.get(action="move")
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.variable, var)
        self.assertEqual(entry.old_role, "predictor")
        self.assertEqual(entry.new_role, "mediator")
        self.assertIsNone(entry.old_layer)
        self.assertEqual(entry.new_layer, 1)

    def test_reorder_records_audit(self):
        p1 = create_variable("predictor", order=1, name="A")
        p2 = create_variable("predictor", order=2, name="B")
        VariableConfigurationService.regenerate_codes()

        VariableConfigurationService.reorder(
            "predictor", [p2.id, p1.id], user=self.user
        )

        entry = VariableConfigAuditLog.objects.get(action="reorder")
        self.assertEqual(entry.detail["role"], "predictor")
        self.assertEqual(entry.detail["ordered_ids"], [p2.id, p1.id])

    def test_add_layer_records_audit(self):
        VariableConfigurationService.add_layer(name="L2", user=self.user)

        entry = VariableConfigAuditLog.objects.get(action="add_layer")
        self.assertEqual(entry.detail["number"], 1)

    def test_deactivate_layer_records_audit(self):
        layer = MediatorLayer.objects.create(number=1)
        VariableConfigurationService.deactivate_layer(
            layer.id, user=self.user
        )
        self.assertTrue(
            VariableConfigAuditLog.objects.filter(
                action="deactivate_layer"
            ).exists()
        )

    def test_move_without_user_records_null_user(self):
        layer1 = MediatorLayer.objects.create(number=1)
        var = create_variable("predictor", order=1, name="P1")
        VariableConfigurationService.regenerate_codes()

        # Tanpa user (misal perubahan programmatik) tetap teraudit,
        # hanya field user-nya NULL.
        VariableConfigurationService.move(var.id, "mediator", 1)

        entry = VariableConfigAuditLog.objects.get(action="move")
        self.assertIsNone(entry.user)
        self.assertEqual(entry.new_role, "mediator")
