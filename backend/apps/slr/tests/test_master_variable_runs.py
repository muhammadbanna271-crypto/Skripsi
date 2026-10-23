from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.master.models import Variable as MasterVariable
from apps.slr.models import SLRRun


class SLRRunMasterVariableTest(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            username="slr-dashboard-staff",
            password="test-password",
            is_staff=True,
        )
        self.active_variable = MasterVariable.objects.create(
            code="X1",
            name="Infrastructure and Accessibility",
            order=1,
            is_active=True,
        )
        self.inactive_variable = MasterVariable.objects.create(
            code="X2",
            name="Inactive Variable",
            order=2,
            is_active=False,
        )

    def test_run_can_reference_master_variable_and_reverse_relation(self):
        first_run = SLRRun.objects.create(
            topic="Infrastructure",
            search_query="Infrastructure",
            master_variable=self.active_variable,
            providers=[],
        )
        second_run = SLRRun.objects.create(
            topic="Access",
            search_query="Access",
            master_variable=self.active_variable,
            providers=[],
        )

        self.assertEqual(first_run.master_variable, self.active_variable)
        self.assertEqual(
            set(self.active_variable.slr_runs.values_list("pk", flat=True)),
            {first_run.pk, second_run.pk},
        )

    def test_dashboard_lists_only_active_master_variables_and_legacy_runs(self):
        SLRRun.objects.create(
            topic="Legacy topic",
            search_query="Legacy topic",
            providers=[],
        )
        self.client.force_login(self.staff_user)

        response = self.client.get("/slr/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["master_variables"]), [self.active_variable])
        self.assertContains(response, "X1 - Infrastructure and Accessibility")
        self.assertContains(response, "Legacy / Not specified")
        self.assertNotContains(response, "X2 - Inactive Variable")
        self.assertNotContains(response, "Research topic")

    @patch("apps.slr.views.dashboard_views.Thread")
    def test_dashboard_create_run_saves_selected_active_master_variable(self, thread):
        self.client.force_login(self.staff_user)

        response = self.client.post("/slr/runs/create/", {
            "master_variable": str(self.active_variable.pk),
            "year_from": "2018",
            "year_to": "2025",
        })

        self.assertRedirects(response, "/slr/")
        run = SLRRun.objects.get(topic="X1 - Infrastructure and Accessibility")
        self.assertEqual(run.master_variable, self.active_variable)
        self.assertEqual(run.search_query, "X1 - Infrastructure and Accessibility")

    def test_dashboard_rejects_inactive_master_variable(self):
        self.client.force_login(self.staff_user)

        response = self.client.post("/slr/runs/create/", {
            "master_variable": str(self.inactive_variable.pk),
        })

        self.assertRedirects(response, "/slr/")
        self.assertFalse(SLRRun.objects.filter(master_variable=self.inactive_variable).exists())

    def test_dashboard_rejects_unknown_master_variable(self):
        self.client.force_login(self.staff_user)

        response = self.client.post("/slr/runs/create/", {
            "master_variable": "999999",
        })

        self.assertRedirects(response, "/slr/")
        self.assertEqual(SLRRun.objects.count(), 0)
