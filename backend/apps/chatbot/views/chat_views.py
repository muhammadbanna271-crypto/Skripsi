import json
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.chatbot.models import ChatbotUsage
from apps.chatbot.services import ClaudeChatService, DeepSeekChatService


SESSION_COUNT_KEY = "chatbot_message_count"

CLAUDE_HISTORY_KEY = "chatbot_history_claude"

DEEPSEEK_HISTORY_KEY = "chatbot_history_deepseek"

CLAUDE_UNLOCKED_KEY = "chatbot_claude_unlocked"


def _trim_history(messages, max_messages=20):
    """
    Potong history TANPA memutus pasangan pesan yang saling terkait
    (assistant tool_calls/tool_use -> tool/tool_result). Memotong
    dengan slicing mentah [-20:] bisa menyisakan pesan role "tool"
    di awal list tanpa pasangan assistant-nya, yang bikin DeepSeek/
    Claude menolak request dengan error 400 pada pesan berikutnya.

    Dikelompokkan per "giliran" (dimulai dari tiap pesan role="user"
    sampai sebelum "user" berikutnya), lalu ambil giliran terakhir
    yang muat dalam max_messages. Pesan system (kalau ada, dan hanya
    kalau berada di posisi paling awal) selalu dipertahankan.
    """

    if not messages:
        return messages

    system = None
    rest = messages

    if messages[0].get("role") == "system":
        system = messages[0]
        rest = messages[1:]

    turns = []
    current = []

    for msg in rest:

        if msg.get("role") == "user" and current:
            turns.append(current)
            current = []

        current.append(msg)

    if current:
        turns.append(current)

    kept = []
    total = 0

    for turn in reversed(turns):

        if kept and total + len(turn) > max_messages:
            break

        kept = turn + kept
        total += len(turn)

    return ([system] if system else []) + kept


def chat_page(request):
    """
    Halaman chat publik -- TIDAK memakai layout admin (tanpa sidebar),
    supaya warga tidak melihat menu Master Data/Survey/dsb.
    """

    return render(
        request,
        "chatbot/public_chat.html",
        {
            "claude_unlocked": request.session.get(
                CLAUDE_UNLOCKED_KEY, False
            ),
            "is_staff": (
                request.user.is_staff or request.user.is_superuser
            ),
        },
    )


@require_POST
@csrf_protect
def unlock_claude(request):

    try:

        payload = json.loads(request.body or "{}")

    except json.JSONDecodeError:

        return JsonResponse(
            {"error": "Format permintaan tidak valid."},
            status=400,
        )

    password = payload.get("password") or ""

    correct_password = settings.CHATBOT_CLAUDE_PASSWORD

    if not correct_password:

        return JsonResponse(
            {
                "error": (
                    "Mesin Claude belum diaktifkan oleh admin "
                    "(password belum diatur)."
                ),
            },
            status=503,
        )

    if password != correct_password:

        return JsonResponse(
            {"error": "Password salah."},
            status=403,
        )

    request.session[CLAUDE_UNLOCKED_KEY] = True

    request.session.modified = True

    return JsonResponse({"unlocked": True})


def _current_month_usage():

    month_key = date.today().strftime("%Y-%m")

    usage, _ = ChatbotUsage.objects.get_or_create(
        month=month_key,
    )

    return usage


@require_POST
@csrf_protect
def chat_message(request):

    try:

        payload = json.loads(request.body or "{}")

    except json.JSONDecodeError:

        return JsonResponse(
            {"error": "Format permintaan tidak valid."},
            status=400,
        )

    message = (payload.get("message") or "").strip()

    engine = payload.get("engine") or "deepseek"

    if engine not in ("claude", "deepseek"):

        return JsonResponse(
            {"error": "Engine tidak dikenali."},
            status=400,
        )

    if not message:

        return JsonResponse(
            {"error": "Pesan tidak boleh kosong."},
            status=400,
        )

    if len(message) > 500:

        return JsonResponse(
            {
                "error": (
                    "Pesan terlalu panjang, maksimal 500 karakter."
                ),
            },
            status=400,
        )

    # ---------------- Password gate khusus Claude ----------------

    if engine == "claude" and not request.session.get(
        CLAUDE_UNLOCKED_KEY, False
    ):

        return JsonResponse(
            {
                "error": (
                    "Mesin Claude terkunci. Masukkan password "
                    "terlebih dahulu."
                ),
            },
            status=403,
        )

    # ---------------- Rate limit per sesi (kedua engine) ----------------

    # Staff/superuser bebas dari batasan pemakaian (tanpa limit).
    is_staff_user = (
        request.user.is_authenticated
        and (request.user.is_staff or request.user.is_superuser)
    )

    count = request.session.get(SESSION_COUNT_KEY, 0)

    limit = settings.CHATBOT_MAX_MESSAGES_PER_SESSION

    if not is_staff_user and count >= limit:

        return JsonResponse(
            {
                "error": (
                    "Kamu sudah mencapai batas jumlah pertanyaan "
                    "untuk sesi ini. Silakan coba lagi nanti."
                ),
            },
            status=429,
        )

    # ---------------- Batas anggaran bulanan (khusus Claude) ----------------

    usage = None

    projected_cost = None

    if engine == "claude":

        usage = _current_month_usage()

        projected_cost = usage.estimated_cost_usd + Decimal(
            str(settings.CHATBOT_ESTIMATED_COST_PER_MESSAGE_USD)
        )

        budget = Decimal(str(settings.CHATBOT_MONTHLY_BUDGET_USD))

        if not is_staff_user and projected_cost > budget:

            return JsonResponse(
                {
                    "error": (
                        "Maaf, mesin Claude untuk bulan ini sedang "
                        "penuh. Coba pakai mesin Planning, Reasoning "
                        "and User Engagement, atau kembali lagi "
                        "bulan depan."
                    ),
                },
                status=429,
            )

    # ---------------- Panggil engine yang sesuai ----------------

    if engine == "claude":

        history_key = CLAUDE_HISTORY_KEY

        history = request.session.get(history_key, [])

        reply, updated_history = ClaudeChatService.ask(
            message, history, is_staff=is_staff_user,
        )

    else:

        history_key = DEEPSEEK_HISTORY_KEY

        history = request.session.get(history_key, [])

        reply, updated_history = DeepSeekChatService.ask(
            message, history, is_staff=is_staff_user,
        )

    # Batasi panjang history yang disimpan supaya session tidak
    # membengkak (simpan pertukaran terakhir saja, tanpa memutus
    # pasangan tool_calls/tool_use -> tool/tool_result).
    request.session[history_key] = _trim_history(updated_history)

    request.session[SESSION_COUNT_KEY] = count + 1

    request.session.modified = True

    if engine == "claude":

        with transaction.atomic():

            usage = (
                ChatbotUsage.objects
                .select_for_update()
                .get(pk=usage.pk)
            )

            usage.message_count += 1

            usage.estimated_cost_usd = projected_cost

            usage.save(
                update_fields=["message_count", "estimated_cost_usd"],
            )

    return JsonResponse(
        {
            "reply": reply,
            "remaining": (
                None
                if is_staff_user
                else max(0, limit - (count + 1))
            ),
        }
    )