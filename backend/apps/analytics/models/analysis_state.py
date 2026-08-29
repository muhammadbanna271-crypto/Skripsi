from django.db import models


class AnalysisState(models.Model):
    """
    Singleton (pk=1) penanda "analysis terakhir dihitung untuk konfigurasi
    yang mana". Menyimpan signature konfigurasi (hash) sehingga staleness
    terdeteksi otomatis:

    - Konfigurasi berubah -> signature berubah -> is_stale() True.
    - Konfigurasi di-revert/undo ke kondisi semula -> signature kembali
      sama -> is_stale() False, TANPA perlu hitung ulang.
    """

    signature = models.CharField(
        max_length=64,
        default="",
        blank=True,
        verbose_name="Config Signature",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Analysis State"
        verbose_name_plural = "Analysis State"

    def save(self, *args, **kwargs):
        # Paksa selalu pk=1 (singleton).
        self.pk = 1
        super().save(*args, **kwargs)

    @staticmethod
    def _current_signature():
        from apps.master.services.variable_configuration_service import (
            VariableConfigurationService,
        )

        return VariableConfigurationService.config_signature()

    @classmethod
    def ensure_baseline(cls):
        """Tetapkan baseline signature kalau masih kosong (mis. setelah
        migrasi). Baseline = konfigurasi saat ini, sehingga perubahan
        berikutnya bisa terdeteksi."""
        obj, _ = cls.objects.get_or_create(pk=1)
        if not obj.signature:
            obj.signature = cls._current_signature()
            obj.save(update_fields=["signature"])
        return obj

    @classmethod
    def is_stale(cls):
        current = cls._current_signature()
        obj, _ = cls.objects.get_or_create(pk=1)
        if not obj.signature:
            # Belum ada baseline -> tetapkan sekarang, anggap tidak stale.
            obj.signature = current
            obj.save(update_fields=["signature"])
            return False
        return current != obj.signature

    @classmethod
    def mark_computed(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        signature = cls._current_signature()
        if obj.signature != signature:
            obj.signature = signature
            obj.save(update_fields=["signature"])
        return obj
