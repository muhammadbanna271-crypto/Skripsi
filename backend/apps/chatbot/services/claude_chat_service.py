import logging
import time

import anthropic
from django.conf import settings

from apps.chatbot.services.prompts import build_system_prompt
from apps.chatbot.tools import execute_tool, tools_schema_for

timing_logger = logging.getLogger("timing")


class ClaudeChatService:
    """
    Engine "Claude" -- dikunci password, dipakai lewat Anthropic API
    dengan format tool-use bawaan Anthropic.
    """

    MAX_TOOL_ITERATIONS = 5

    @classmethod
    def ask(cls, message, history=None, is_staff=False):
        """
        message: teks pertanyaan warga (str)
        history: list pesan sebelumnya, format Anthropic messages
                 (biasanya disimpan di session Django)
        is_staff: bila False (visitor), tool riset internal tidak tersedia.

        Return: (reply_text, updated_history)
        """

        if not settings.ANTHROPIC_API_KEY:

            return (
                (
                    "Maaf, mesin Claude belum dikonfigurasi oleh "
                    "admin (API key belum diatur)."
                ),
                history or [],
            )

        client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
        )

        messages = list(history or [])

        messages.append(
            {"role": "user", "content": message}
        )

        for _ in range(cls.MAX_TOOL_ITERATIONS):

            t0 = time.perf_counter()
            response = client.messages.create(
                model=settings.CHATBOT_MODEL,
                max_tokens=1024,
                system=build_system_prompt(),
                tools=tools_schema_for(is_staff),
                messages=messages,
            )
            timing_logger.info(
                "Claude LLM call: %.0f ms (model=%s, stop_reason=%s)",
                (time.perf_counter() - t0) * 1000,
                settings.CHATBOT_MODEL,
                response.stop_reason,
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": [
                        block.model_dump()
                        for block in response.content
                    ],
                }
            )

            if response.stop_reason != "tool_use":

                final_text = "".join(

                    block.text

                    for block in response.content

                    if block.type == "text"

                )

                return final_text, messages

            tool_results = []

            for block in response.content:

                if block.type == "tool_use":

                    result = execute_tool(
                        block.name,
                        block.input,
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        }
                    )

            messages.append(
                {
                    "role": "user",
                    "content": tool_results,
                }
            )

        return (
            (
                "Maaf, pertanyaan ini terlalu kompleks untuk saya "
                "proses saat ini. Coba tanyakan dengan lebih spesifik."
            ),
            messages,
        )
