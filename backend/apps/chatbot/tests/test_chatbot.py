import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.chatbot.models import ChatbotUsage


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    CHATBOT_CLAUDE_PASSWORD="secret",
    # Pastikan tidak ada panggilan API riil saat test.
    ANTHROPIC_API_KEY="",
    DEEPSEEK_API_KEY="",
)
class ChatbotViewTest(TestCase):

    MESSAGE_URL = "/chatbot/api/message/"
    UNLOCK_URL = "/chatbot/api/unlock/"

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            "staff", "s@example.com", "pass", is_staff=True
        )
        self.visitor = User.objects.create_user(
            "visitor", "v@example.com", "pass"
        )

    def _post(self, client, message="hi", engine="deepseek"):
        return client.post(
            self.MESSAGE_URL,
            data=json.dumps({"message": message, "engine": engine}),
            content_type="application/json",
        )

    def _set_session_count(self, client, count):
        session = client.session
        session["chatbot_message_count"] = count
        session.save()

    def _unlock_claude(self, client):
        return client.post(
            self.UNLOCK_URL,
            data=json.dumps({"password": "secret"}),
            content_type="application/json",
        )

    def test_empty_message_400(self):
        self.client.force_login(self.visitor)
        self.assertEqual(self._post(self.client, message="   ").status_code, 400)

    def test_message_too_long_400(self):
        self.client.force_login(self.visitor)
        self.assertEqual(
            self._post(self.client, message="x" * 501).status_code, 400
        )

    def test_invalid_engine_400(self):
        self.client.force_login(self.visitor)
        self.assertEqual(self._post(self.client, engine="nope").status_code, 400)

    def test_visitor_rate_limited_429(self):
        self.client.force_login(self.visitor)
        self._set_session_count(self.client, 9999)
        self.assertEqual(self._post(self.client).status_code, 429)

    def test_staff_not_rate_limited(self):
        self.client.force_login(self.staff)
        self._set_session_count(self.client, 9999)
        # Staff bebas limit -> lanjut ke engine (DeepSeek key kosong -> 200).
        self.assertEqual(self._post(self.client).status_code, 200)

    def test_claude_locked_requires_password(self):
        self.client.force_login(self.visitor)
        self.assertEqual(
            self._post(self.client, engine="claude").status_code, 403
        )

    def test_claude_unlock_wrong_password(self):
        self.client.force_login(self.visitor)
        r = self.client.post(
            self.UNLOCK_URL,
            data=json.dumps({"password": "salah"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    def test_visitor_claude_budget_exceeded(self):
        self.client.force_login(self.visitor)
        self._unlock_claude(self.client)

        ChatbotUsage.objects.create(
            month=date.today().strftime("%Y-%m"),
            estimated_cost_usd="9.99",
        )

        with override_settings(
            CHATBOT_MONTHLY_BUDGET_USD="10",
            CHATBOT_ESTIMATED_COST_PER_MESSAGE_USD="1",
        ):
            r = self._post(self.client, engine="claude")

        self.assertEqual(r.status_code, 429)

    def test_staff_claude_budget_bypassed(self):
        self.client.force_login(self.staff)
        self._unlock_claude(self.client)

        ChatbotUsage.objects.create(
            month=date.today().strftime("%Y-%m"),
            estimated_cost_usd="9.99",
        )

        with override_settings(
            CHATBOT_MONTHLY_BUDGET_USD="10",
            CHATBOT_ESTIMATED_COST_PER_MESSAGE_USD="1",
        ):
            r = self._post(self.client, engine="claude")

        # Staff bebas budget -> lanjut ke engine (Claude key kosong -> 200).
        self.assertEqual(r.status_code, 200)
