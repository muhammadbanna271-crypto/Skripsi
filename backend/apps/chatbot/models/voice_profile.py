from django.db import models

from common.models import BaseModel


class VoiceProfile(BaseModel):
    """
    Metadata suara (voice) untuk Text-to-Speech PRUDENCE.

    Disiapkan untuk custom voice / voice-cloning di masa depan. TTS saat ini
    memakai ``speechSynthesis`` browser yang TIDAK mendukung custom voice ID
    server-side, jadi record ini hanya metadata — belum dipakai runtime.
    """

    name = models.CharField(max_length=100, verbose_name="Nama Suara")

    provider = models.CharField(max_length=100, verbose_name="Provider TTS")

    provider_voice_id = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Provider Voice ID",
    )

    language = models.CharField(
        max_length=20,
        default="id-ID",
        verbose_name="Bahasa",
    )

    active = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        db_table = "chatbot_voice_profile"
        verbose_name = "Profil Suara"
        verbose_name_plural = "Profil Suara"
        ordering = ["name"]

    def __str__(self):
        return self.name
