from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from apps.master.services.excel_import_service import (
    DISTRICT_HEADERS,
    DISTRICT_SAMPLE,
    VARIABLE_HEADERS,
    VARIABLE_SAMPLE,
    VILLAGE_HEADERS,
    VILLAGE_SAMPLE,
    DistrictExcelImportService,
    ExcelImportError,
    VariableExcelImportService,
    VillageExcelImportService,
    district_template,
    variable_template,
    village_template,
)

XLSX_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


class StaffOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Hanya admin (staff/superuser) yang boleh impor data master."""

    def test_func(self):
        user = self.request.user
        return user.is_staff or user.is_superuser

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(
            self.request, "Kamu tidak punya izin untuk mengakses halaman ini."
        )
        return redirect("dashboard:dashboard")


class BaseExcelImportView(StaffOnlyMixin, View):
    template_name = "master/import/import.html"
    service = None
    title = ""
    description = ""
    headers = []
    sample = []
    rules = []
    template_url_name = ""
    success_url_name = ""

    def _context(self, **extra):
        return {
            "title": self.title,
            "description": self.description,
            "headers": self.headers,
            "sample": self.sample,
            "rules": self.rules,
            "template_url_name": self.template_url_name,
            "list_url_name": self.success_url_name,
            **extra,
        }

    def get(self, request):
        return render(request, self.template_name, self._context())

    def post(self, request):
        uploaded = request.FILES.get("file")
        if uploaded is None:
            messages.error(request, "Pilih file Excel (.xlsx) terlebih dahulu.")
            return redirect(request.path)

        try:
            result = self.service.import_file(uploaded)
        except ExcelImportError as error:
            messages.error(request, str(error))
            return redirect(request.path)

        if not result.ok:
            return render(
                request,
                self.template_name,
                self._context(result=result, filename=uploaded.name),
            )

        summary = ", ".join(
            f"{count} {label}" for label, count in result.created.items()
        )
        skipped = ", ".join(
            f"{count} {label}" for label, count in result.skipped.items()
        )
        text = f"Import berhasil: {summary or 'tidak ada data baru'}."
        if skipped:
            text += f" Dilewati: {skipped}."
        messages.success(request, text)
        return redirect(self.success_url_name)


class DistrictImportView(BaseExcelImportView):
    service = DistrictExcelImportService
    title = "Import Kecamatan dari Excel"
    description = "Unggah file Excel berisi daftar kecamatan beserta ID-nya."
    headers = DISTRICT_HEADERS
    sample = DISTRICT_SAMPLE
    rules = [
        "File berformat .xlsx; data dibaca dari sheet pertama.",
        "Baris 1 adalah header, data mulai baris 2.",
        "ID Kecamatan harus angka dan unik; nama kecamatan unik.",
        "Impor kecamatan sebelum desa supaya ID Kecamatan sesuai file.",
        "Jika ada satu baris yang salah, tidak ada data yang disimpan.",
    ]
    template_url_name = "master:district-import-template"
    success_url_name = "master:district-list"


class VillageImportView(BaseExcelImportView):
    service = VillageExcelImportService
    title = "Import Desa dari Excel"
    description = (
        "Unggah file Excel berisi daftar desa dan kecamatan. Kecamatan yang "
        "belum ada akan dibuat otomatis (sebaiknya impor Kecamatan dulu)."
    )
    headers = VILLAGE_HEADERS
    sample = VILLAGE_SAMPLE
    rules = [
        "File berformat .xlsx; data dibaca dari sheet pertama.",
        "Baris 1 adalah header, data mulai baris 2.",
        "ID Desa harus angka dan unik; nama desa unik.",
        "Jika ada satu baris yang salah, tidak ada data yang disimpan.",
    ]
    template_url_name = "master:village-import-template"
    success_url_name = "master:village-list"


class VariableImportView(BaseExcelImportView):
    service = VariableExcelImportService
    title = "Import Variabel, Indikator, dan Pernyataan dari Excel"
    description = (
        "Satu file untuk tiga data master: variabel, indikator, dan "
        "pernyataan kuesioner. Satu baris berisi satu pernyataan."
    )
    headers = VARIABLE_HEADERS
    sample = VARIABLE_SAMPLE
    rules = [
        "File berformat .xlsx; data dibaca dari sheet pertama.",
        "Baris 1 adalah header, data mulai baris 2.",
        "Kode Variabel diawali X (predictor), Y (mediator), atau Z "
        "(response), contoh X1. Kode Indikator contoh X1.1 dan harus sesuai "
        "dengan variabelnya.",
        "Nama variabel dan nama indikator harus unik. Pernyataan disimpan "
        "sebagai pertanyaan kuesioner.",
        "Jenis Jawaban: Skala Likert (1-5), Ya/Tidak, Angka Bulat, "
        "Desimal, Teks, atau Pilihan Ganda.",
        "Variabel Y masuk ke Mediator Layer 1. Kode final dibuat ulang "
        "sistem berdasarkan role dan urutan.",
        "Jika ada satu baris yang salah, tidak ada data yang disimpan.",
    ]
    template_url_name = "master:variable-import-template"
    success_url_name = "master:variable-list"


class BaseTemplateDownloadView(StaffOnlyMixin, View):
    builder = None
    filename = ""

    def get(self, request):
        response = HttpResponse(content_type=XLSX_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{self.filename}"'
        type(self).builder().save(response)
        return response


class DistrictImportTemplateView(BaseTemplateDownloadView):
    builder = staticmethod(district_template)
    filename = "contoh_import_kecamatan.xlsx"


class VillageImportTemplateView(BaseTemplateDownloadView):
    builder = staticmethod(village_template)
    filename = "contoh_import_desa.xlsx"


class VariableImportTemplateView(BaseTemplateDownloadView):
    builder = staticmethod(variable_template)
    filename = "contoh_import_variabel.xlsx"
