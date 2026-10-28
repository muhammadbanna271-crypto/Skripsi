"""
Navigasi admin:
- setelah Add/Edit/Delete anak (Indicator, Questionnaire, Response) user
  kembali ke halaman induk yang sedang dikerjakan, bukan ke list utama;
- sidebar hanya menandai SATU menu aktif.
"""

import datetime
import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.master.models import District, Indicator, Questionnaire, Village
from apps.master.tests.factories import (
    create_indicator,
    create_questionnaire,
    create_variable,
)
from apps.respondent.models import Respondent
from apps.response.models import Response
from apps.survey.models import Survey, SurveyVillage


def active_menu_labels(html):
    """Label semua link SIDEBAR yang bertanda active."""
    sidebar = html.split('<div class="sidebar">', 1)[1].split(
        "sidebar-footer", 1
    )[0]
    html = sidebar
    return [
        re.sub(r"<[^>]+>", "", match).strip()
        for match in re.findall(
            r'<a[^>]*class="nav-link active"[^>]*>(.*?)</a>', html, re.S
        )
    ]


class StaffTestCase(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "staff", password="x", is_staff=True
        )
        self.client.force_login(self.user)


class IndicatorNavigationTests(StaffTestCase):

    def setUp(self):
        super().setUp()
        self.x1 = create_variable("predictor", order=1)
        self.x2 = create_variable("predictor", order=2)

    def payload(self, variable, code="N1.1"):
        return {
            "variable": variable.pk,
            "code": code,
            "name": "Indikator",
            "description": "",
            "weight": "1",
            "is_active": "on",
        }

    def test_create_returns_to_variable_page(self):
        response = self.client.post(
            reverse("master:indicator-create"), self.payload(self.x1)
        )

        self.assertRedirects(
            response,
            reverse("master:indicator-by-variable", args=[self.x1.pk]),
            fetch_redirect_response=False,
        )
        self.assertTrue(Indicator.objects.filter(code="N1.1").exists())

    def test_create_form_preselects_and_cancels_to_variable(self):
        response = self.client.get(
            reverse("master:indicator-create") + f"?variable={self.x2.pk}"
        )

        self.assertEqual(
            response.context["form"].initial["variable"], str(self.x2.pk)
        )
        self.assertEqual(
            response.context["cancel_url"],
            reverse("master:indicator-by-variable", args=[self.x2.pk]),
        )

    def test_create_without_variable_cancels_to_main_list(self):
        response = self.client.get(reverse("master:indicator-create"))

        self.assertEqual(
            response.context["cancel_url"], reverse("master:indicator-list")
        )

    def test_invalid_variable_param_is_ignored(self):
        response = self.client.get(
            reverse("master:indicator-create") + "?variable=abc"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("variable", response.context["form"].initial)

    def test_variable_page_add_button_carries_variable(self):
        response = self.client.get(
            reverse("master:indicator-by-variable", args=[self.x1.pk])
        )

        self.assertContains(
            response,
            reverse("master:indicator-create") + f"?variable={self.x1.pk}",
        )

    def test_update_returns_to_variable_page(self):
        indicator = create_indicator(self.x1, code="U1.1")

        response = self.client.post(
            reverse("master:indicator-update", args=[indicator.pk]),
            self.payload(self.x1, code="U1.1"),
        )

        self.assertRedirects(
            response,
            reverse("master:indicator-by-variable", args=[self.x1.pk]),
            fetch_redirect_response=False,
        )

    def test_delete_returns_to_variable_page(self):
        indicator = create_indicator(self.x1)

        response = self.client.post(
            reverse("master:indicator-delete", args=[indicator.pk])
        )

        self.assertRedirects(
            response,
            reverse("master:indicator-by-variable", args=[self.x1.pk]),
            fetch_redirect_response=False,
        )
        self.assertFalse(Indicator.objects.filter(pk=indicator.pk).exists())

    def test_detail_update_delete_pages_link_back_to_variable(self):
        indicator = create_indicator(self.x1)
        back = reverse("master:indicator-by-variable", args=[self.x1.pk])

        for name in ("indicator-detail", "indicator-update",
                     "indicator-delete"):
            with self.subTest(page=name):
                response = self.client.get(
                    reverse(f"master:{name}", args=[indicator.pk])
                )
                self.assertContains(response, f'href="{back}"')


class QuestionnaireNavigationTests(StaffTestCase):

    def setUp(self):
        super().setUp()
        self.variable = create_variable("predictor")
        self.indicator = create_indicator(self.variable)
        self.other = create_indicator(self.variable)

    def payload(self, indicator, order=1):
        return {
            "indicator": indicator.pk,
            "question": "Pertanyaan?",
            "answer_type": "likert",
            "question_order": order,
            "is_required": "on",
            "is_active": "on",
        }

    def test_create_returns_to_indicator_page(self):
        response = self.client.post(
            reverse("master:questionnaire-create"),
            self.payload(self.indicator),
        )

        self.assertRedirects(
            response,
            reverse("master:questionnaire-by-indicator",
                    args=[self.indicator.pk]),
            fetch_redirect_response=False,
        )

    def test_create_form_preselects_indicator(self):
        response = self.client.get(
            reverse("master:questionnaire-create")
            + f"?indicator={self.other.pk}"
        )

        self.assertEqual(
            response.context["form"].initial["indicator"], str(self.other.pk)
        )
        self.assertEqual(
            response.context["cancel_url"],
            reverse("master:questionnaire-by-indicator",
                    args=[self.other.pk]),
        )

    def test_indicator_page_add_button_carries_indicator(self):
        response = self.client.get(
            reverse("master:questionnaire-by-indicator",
                    args=[self.indicator.pk])
        )

        self.assertContains(
            response,
            reverse("master:questionnaire-create")
            + f"?indicator={self.indicator.pk}",
        )

    def test_update_and_delete_return_to_indicator_page(self):
        questionnaire = create_questionnaire(self.indicator)
        target = reverse("master:questionnaire-by-indicator",
                         args=[self.indicator.pk])

        response = self.client.post(
            reverse("master:questionnaire-update", args=[questionnaire.pk]),
            self.payload(self.indicator),
        )
        self.assertRedirects(response, target, fetch_redirect_response=False)

        response = self.client.post(
            reverse("master:questionnaire-delete", args=[questionnaire.pk])
        )
        self.assertRedirects(response, target, fetch_redirect_response=False)
        self.assertFalse(
            Questionnaire.objects.filter(pk=questionnaire.pk).exists()
        )


class ResponseNavigationTests(StaffTestCase):

    def setUp(self):
        super().setUp()
        district = District.objects.create(code="D", name="D")
        village = Village.objects.create(code="1", name="V", district=district)
        survey = Survey.objects.create(
            name="S",
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2024, 12, 31),
        )
        survey_village = SurveyVillage.objects.create(
            survey=survey, village=village
        )
        self.respondent = Respondent.objects.create(
            survey_village=survey_village,
            nik="N1",
            name="R1",
            gender="M",
            birth_date=datetime.date(2000, 1, 1),
            address="x",
        )
        self.questionnaire = create_questionnaire(
            create_indicator(create_variable("predictor"))
        )
        self.detail = reverse(
            "response:response-detail", args=[self.respondent.pk]
        )

    def payload(self):
        return {
            "respondent": self.respondent.pk,
            "questionnaire": self.questionnaire.pk,
            "answer_integer": 3,
            "answer_text": "",
            "score": "3",
        }

    def test_create_update_delete_return_to_respondent_detail(self):
        response = self.client.post(
            reverse("response:response-create"), self.payload()
        )
        self.assertRedirects(response, self.detail,
                             fetch_redirect_response=False)

        answer = Response.objects.get()

        response = self.client.post(
            reverse("response:response-update", args=[answer.pk]),
            self.payload(),
        )
        self.assertRedirects(response, self.detail,
                             fetch_redirect_response=False)

        response = self.client.post(
            reverse("response:response-delete", args=[answer.pk])
        )
        self.assertRedirects(response, self.detail,
                             fetch_redirect_response=False)

    def test_detail_page_add_button_carries_respondent(self):
        response = self.client.get(self.detail)

        self.assertContains(
            response,
            reverse("response:response-create")
            + f"?respondent={self.respondent.pk}",
        )

    def test_create_form_preselects_respondent(self):
        response = self.client.get(
            reverse("response:response-create")
            + f"?respondent={self.respondent.pk}"
        )

        self.assertEqual(
            response.context["form"].initial["respondent"],
            str(self.respondent.pk),
        )
        self.assertEqual(response.context["cancel_url"], self.detail)


class SidebarHighlightTests(StaffTestCase):

    def active(self, name):
        return active_menu_labels(
            self.client.get(reverse(name)).content.decode()
        )

    def test_survey_village_highlights_only_survey_village(self):
        self.assertEqual(self.active("survey:survey-village-list"),
                         ["Survey Village"])

    def test_survey_highlights_only_survey(self):
        self.assertEqual(self.active("survey:survey-list"), ["Survey"])

    def test_ml_dashboard_highlights_only_ml_dashboard(self):
        self.assertEqual(self.active("analytics:ml-dashboard"),
                         ["ML Dashboard"])

    def test_analytics_highlights_only_analytics(self):
        self.assertEqual(self.active("analytics:dashboard"), ["Analytics"])

    def test_dashboard_highlights_single_menu_for_staff(self):
        self.assertEqual(self.active("dashboard:dashboard"), ["Dashboard"])

    def test_each_master_menu_highlights_exactly_one(self):
        expected = {
            "master:district-list": "District",
            "master:village-list": "Village",
            "master:cluster-list": "Cluster",
            "master:variable-list": "Variable",
            "master:indicator-list": "Indicator",
            "master:questionnaire-list": "Questionnaire",
            "respondent:respondent-list": "Respondent",
            "response:response-list": "Response",
        }
        for name, label in expected.items():
            with self.subTest(page=name):
                self.assertEqual(self.active(name), [label])

    def test_child_pages_keep_parent_menu_highlighted(self):
        variable = create_variable("predictor")
        page = reverse("master:indicator-by-variable", args=[variable.pk])

        self.assertEqual(
            active_menu_labels(self.client.get(page).content.decode()),
            ["Indicator"],
        )
