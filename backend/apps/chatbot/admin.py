from django.contrib import admin

from apps.chatbot.models import VoiceProfile


@admin.register(VoiceProfile)
class VoiceProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "provider",
        "provider_voice_id",
        "language",
        "active",
        "updated_at",
    )
    search_fields = ("name", "provider", "provider_voice_id")
    list_filter = ("provider", "language", "active")
    ordering = ("name",)
