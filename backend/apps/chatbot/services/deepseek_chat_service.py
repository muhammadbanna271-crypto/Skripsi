import json
import logging
import time

import requests
from django.conf import settings

from apps.chatbot.services.prompts import build_system_prompt
from apps.chatbot.tools import (
    execute_tool,
    to_openai_tools_schema,
    tools_schema_for,
)

timing_logger = logging.getLogger("timing")


DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

logger = logging.getLogger(__name__)


class DeepSeekChatService:
    """
    Engine "Planning, Reasoning and User Engagement" -- bebas akses
    tanpa password, dipakai lewat DeepSeek API (format OpenAI-compatible
    function calling, BEDA struktur dari Anthropic tool-use).
    """

    MAX_TOOL_ITERATIONS = 5

    @classmethod
    def ask(cls, message, history=None, is_staff=False):
        """
        message: teks pertanyaan warga (str)
        history: list pesan sebelumnya, format OpenAI-style messages
                 (disimpan terpisah dari history Claude di session)
        is_staff: bila False (visitor), tool riset internal tidak tersedia.

        Return: (reply_text, updated_history)
        """

        if not settings.DEEPSEEK_API_KEY:

            return (
                (
                    "Maaf, mesin DeepSeek belum dikonfigurasi oleh "
                    "admin (API key belum diatur)."
                ),
                history or [],
            )

        messages = list(history or [])

        if not messages:

            messages.append(
                {"role": "system", "content": build_system_prompt()}
            )

        messages.append(
            {"role": "user", "content": message}
        )

        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }

        for _ in range(cls.MAX_TOOL_ITERATIONS):

            body = {
                "model": settings.DEEPSEEK_MODEL,
                "messages": messages,
                "tools": to_openai_tools_schema(tools_schema_for(is_staff)),
                "max_tokens": 1024,
            }

            t0 = time.perf_counter()
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=body,
                timeout=30,
            )
            timing_logger.info(
                "DeepSeek API call: %.0f ms (status=%s)",
                (time.perf_counter() - t0) * 1000,
                response.status_code,
            )

            if response.status_code != 200:

                # Catat body respons asli ke log server -- status code
                # saja nggak cukup buat tahu penyebabnya (mis. "messages
                # must alternate roles", saldo habis, dsb). Cek log
                # server ("DeepSeek API error ...") untuk detailnya.
                logger.error(
                    "DeepSeek API error (status %s): %s",
                    response.status_code,
                    response.text[:2000],
                )

                # Kosongkan history sesi ini supaya kalau penyebabnya
                # riwayat pesan yang korup/tidak valid, percakapan
                # berikutnya mulai bersih dari nol (self-healing)
                # alih-alih macet error terus-menerus.
                return (
                    (
                        "Maaf, mesin DeepSeek sedang bermasalah "
                        f"(status {response.status_code}). "
                        "Coba lagi sebentar lagi ya."
                    ),
                    [],
                )

            data = response.json()

            choice = data["choices"][0]

            message_obj = choice["message"]

            messages.append(message_obj)

            tool_calls = message_obj.get("tool_calls")

            if not tool_calls:

                return message_obj.get("content", ""), messages

            for call in tool_calls:

                function_name = call["function"]["name"]

                try:

                    arguments = json.loads(
                        call["function"]["arguments"] or "{}"
                    )

                except json.JSONDecodeError:

                    arguments = {}

                result = execute_tool(function_name, arguments)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": str(result),
                    }
                )

        return (
            (
                "Maaf, pertanyaan ini terlalu kompleks untuk saya "
                "proses saat ini. Coba tanyakan dengan lebih spesifik."
            ),
            messages,
        )