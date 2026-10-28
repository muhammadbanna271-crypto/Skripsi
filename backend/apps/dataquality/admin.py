from django.contrib import admin, messages
from django.http import HttpResponse

from .models import ExecutionLog, QualityScore, RejectionLog
from .reporting import build_workbook


@admin.register(ExecutionLog)
class ExecutionLogAdmin(admin.ModelAdmin):
    list_display = (
        "execution_id", "status", "n_input", "n_accepted",
        "n_rejected", "n_output", "delta_n", "started_at",
    )
    list_filter = ("status",)
    actions = ["unduh_laporan_xlsx"]

    @admin.action(description="Unduh laporan validasi (xlsx) - pilih satu eksekusi")
    def unduh_laporan_xlsx(self, request, queryset):
        # Laporan dibuat hanya saat admin memintanya; upload tidak memicu file.
        if queryset.count() != 1:
            self.message_user(
                request, "Pilih tepat satu eksekusi.", level=messages.ERROR
            )
            return None
        execution = queryset.first()
        response = HttpResponse(
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )
        response["Content-Disposition"] = (
            f'attachment; filename="laporan_dq_{execution.execution_id}.xlsx"'
        )
        build_workbook(execution).save(response)
        return response


@admin.register(RejectionLog)
class RejectionLogAdmin(admin.ModelAdmin):
    list_display = (
        "execution", "checkpoint", "source_row", "column_name",
        "dimension", "rule",
    )
    list_filter = ("checkpoint", "dimension")


@admin.register(QualityScore)
class QualityScoreAdmin(admin.ModelAdmin):
    list_display = (
        "execution", "checkpoint", "dimension",
        "n_checked", "n_satisfied", "score",
    )
