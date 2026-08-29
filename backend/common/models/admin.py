"""
Tambahin ke backend/common/admin.py (buat file baru kalau belum
ada admin.py di app common)
"""

from django.contrib import admin

from common.models import SurveyAccessSetting


@admin.register(SurveyAccessSetting)
class SurveyAccessSettingAdmin(admin.ModelAdmin):

    list_display = ("allow_public_input", "updated_at")

    def has_add_permission(self, request):
        # Nggak boleh nambah baris baru (singleton, cuma 1 baris).
        # Kalau baris belum ada, otomatis dibuat pas pertama kali
        # diakses (lihat get_or_create di model).
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # PENTING: cuma superuser yang boleh ubah toggle ini,
        # staff biasa (walau dikasih akses admin) tetap tidak
        # bisa ganti setting ini.
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser