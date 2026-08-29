import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.master.models import Variable

from .factories import create_variable


@override_settings(ALLOWED_HOSTS=["testserver"])
class VariableConfigApiTest(TestCase):

    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            "su", "su@example.com", "pass"
        )
        self.staff = User.objects.create_user(
            "staff", "staff@example.com", "pass", is_staff=True
        )
        self.visitor = User.objects.create_user(
            "visitor", "visitor@example.com", "pass"
        )

        create_variable("predictor", order=1, name="P1")
        create_variable("predictor", order=2, name="P2")
        create_variable("response", order=1, name="R1")

    def test_anonymous_is_redirected(self):
        response = self.client.get(reverse("master:variable-config"))
        self.assertIn(response.status_code, (301, 302))

    def test_visitor_can_read_configuration(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse("master:variable-config"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_visitor_cannot_reorder(self):
        self.client.force_login(self.visitor)
        response = self.client.post(
            reverse("master:variable-reorder"),
            data=json.dumps({"role": "predictor", "ordered_ids": []}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_visitor_cannot_move(self):
        self.client.force_login(self.visitor)
        response = self.client.post(
            reverse("master:variable-move"),
            data=json.dumps(
                {"variable_id": 1, "new_role": "response"}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_visitor_cannot_add_layer(self):
        self.client.force_login(self.visitor)
        response = self.client.post(
            reverse("master:layer-add"),
            data=json.dumps({"name": "L"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_reorder(self):
        self.client.force_login(self.staff)
        ids = list(
            Variable.objects.filter(role="predictor")
            .order_by("order")
            .values_list("id", flat=True)
        )
        response = self.client.post(
            reverse("master:variable-reorder"),
            data=json.dumps(
                {"role": "predictor", "ordered_ids": ids}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_superuser_can_add_layer(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("master:layer-add"),
            data=json.dumps({"name": "Layer 2"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_invalid_role_returns_400(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("master:variable-move"),
            data=json.dumps(
                {"variable_id": 1, "new_role": "nope"}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
