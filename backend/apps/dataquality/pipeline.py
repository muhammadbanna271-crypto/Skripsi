"""
Orkestrasi:

Read Excel -> Schema Gate -> P1 -> Accept/Reject -> Database -> P2
-> pipeline existing (agregasi skor) -> Output

Penyimpanan memakai ResponseBulkImportService.import_excel yang sudah
ada (dibatasi ke baris yang diterima). Skor/agregasi/TOPSIS/K-Means
tidak diubah.
"""

import dataclasses
import logging
from io import BytesIO
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException

from django.conf import settings
from django.utils import timezone

from apps.analytics.services.score_aggregation_service import (
    ScoreAggregationService,
)
from apps.respondent.models import Respondent
from apps.response.services.bulk_import_service import (
    BulkImportError,
    ResponseBulkImportService,
)

from .fingerprint import database_state
from .models import ExecutionLog, QualityScore, RejectionLog
from .reader import (
    SchemaError,
    expected_indicator_codes,
    indicators_without_questionnaire,
    read_bytes,
    read_source,
    registered_village_codes,
    schema_gate,
    sha256_of,
)
from . import wording
from .rules import (
    CHECKPOINT_P1,
    CHECKPOINT_P2,
    DIMENSIONS,
    RULES_VERSION,
)
from .validators import run_p1
from .verification import (
    ACTION_NOT_STORED,
    ACTION_REMOVED,
    run_p2,
)

logger = logging.getLogger(__name__)


def allowed_persons():
    """
    Himpunan nilai Person yang diizinkan (huruf kecil), dari
    settings.DATAQUALITY_ALLOWED_PERSONS. None = tidak dibatasi,
    karena repository tidak memuat daftar jabatan.
    """

    configured = getattr(settings, "DATAQUALITY_ALLOWED_PERSONS", None)
    if configured is None:
        return None
    return {str(value).strip().lower() for value in configured}


def run_config():
    """Konfigurasi aturan yang berlaku; disimpan agar terlihat di report."""

    persons = allowed_persons()
    return {
        "rules_version": RULES_VERSION,
        "person_domain_rule": "active" if persons is not None else "inactive",
        "allowed_persons": sorted(persons) if persons is not None else None,
    }


def _save_rejections(execution, violations):
    RejectionLog.objects.bulk_create(
        [
            RejectionLog(
                execution=execution,
                respondent_id=v.respondent_id,
                source_row=v.row_number,
                column_name=v.column,
                original_value="" if v.value is None else str(v.value),
                value_type=type(v.value).__name__,
                dimension=v.dimension,
                rule=v.rule,
                checkpoint=v.checkpoint,
                reason=v.reason,
                db_value="" if v.db_value is None else str(v.db_value),
                record_action=v.record_action,
                related_row=v.related_row,
            )
            for v in violations
        ]
    )


def _save_quality(execution, checkpoint, counts):
    QualityScore.objects.bulk_create(
        [
            QualityScore(
                execution=execution,
                checkpoint=checkpoint,
                dimension=dimension,
                n_checked=counts[dimension].checked,
                n_satisfied=counts[dimension].satisfied,
                score=counts[dimension].score,
            )
            for dimension in DIMENSIONS
        ]
    )


def _finish(execution, status, message=""):
    execution.status = status
    execution.error_message = message
    execution.finished_at = timezone.now()
    execution.save()
    return execution


class ValidatedImportService:

    @classmethod
    def run(cls, file, survey=None, *, run_scoring=True, ground_truth=None):
        """
        Jalankan satu eksekusi import tervalidasi dan kembalikan
        ExecutionLog-nya. Kegagalan schema/proses dicatat di log
        (tidak di-raise); cacat baris tidak menghentikan dataset.

        ground_truth (opsional): dict hasil injection.inject(); disimpan
        di output_summary agar dq_report dapat mengekspor dan
        mengevaluasinya terhadap rejection log.
        """

        summary = {"config": run_config()}
        if ground_truth is not None:
            summary["ground_truth"] = ground_truth

        execution = ExecutionLog.objects.create(
            survey=survey,
            started_at=timezone.now(),
            rules_version=RULES_VERSION,
            output_summary=summary,
        )

        try:
            data, filename = read_bytes(file)
            execution.source_filename = filename
            execution.source_sha256 = sha256_of(data)
            execution.save()

            return cls._execute(execution, data, survey, run_scoring)

        except Exception as error:
            logger.exception(
                "Eksekusi data-quality %s gagal", execution.execution_id
            )
            unreadable = isinstance(
                error, (BadZipFile, InvalidFileException)
            )
            execution.output_summary["user_message"] = (
                wording.MSG_UNREADABLE_FILE
                if unreadable
                else wording.MSG_UNEXPECTED
            )
            return _finish(
                execution,
                ExecutionLog.STATUS_FAILED_PROCESS,
                f"{type(error).__name__}: {error}",
            )

    @classmethod
    def _execute(cls, execution, data, survey, run_scoring):

        # ---- baca + schema gate ---------------------------------
        try:
            source = read_source(data)
            execution.n_input = len(source.rows)
            indicator_codes = expected_indicator_codes()
            schema_gate(source.column_map, indicator_codes)
        except BulkImportError as error:
            execution.output_summary["user_message"] = (
                wording.msg_header_not_found(error)
            )
            return _finish(
                execution, ExecutionLog.STATUS_FAILED_SCHEMA, str(error)
            )
        except SchemaError as error:
            execution.output_summary["missing_columns"] = error.missing
            execution.output_summary["user_message"] = str(error)
            return _finish(
                execution, ExecutionLog.STATUS_FAILED_SCHEMA, str(error)
            )

        execution.output_summary["indicators_without_questionnaire"] = (
            indicators_without_questionnaire()
        )

        # ---- P1 --------------------------------------------------
        p1 = run_p1(
            source.rows,
            indicator_codes,
            registered_village_codes(),
            allowed_persons(),
        )

        _save_rejections(execution, p1.violations)
        _save_quality(execution, CHECKPOINT_P1, p1.counts)

        execution.n_accepted = len(p1.accepted_rows)
        execution.n_rejected_p1 = len(p1.rejected_rows)
        execution.save()

        # ---- database (import existing, hanya baris diterima) ---
        accepted_numbers = {row.row_number for row in p1.accepted_rows}
        import_result = {
            "created_respondent": 0,
            "updated_respondent": 0,
            "created_response": 0,
            "skipped_rows": [],
        }

        if accepted_numbers:
            import_result = ResponseBulkImportService.import_excel(
                BytesIO(data),
                survey,
                only_rows=accepted_numbers,
            )

        # ---- P2 --------------------------------------------------
        p2 = run_p2(p1.accepted_rows, indicator_codes)

        # Tindakan terhadap rekaman dicatat pada setiap discrepancy, dan
        # nilai sumber vs database sudah ada di db_value / original_value.
        p2_violations = [
            dataclasses.replace(
                v,
                record_action=(
                    ACTION_NOT_STORED
                    if v.row_number in p2.lost_rows
                    else ACTION_REMOVED
                    if v.row_number in p2.rejected_rows
                    else ""
                ),
            )
            for v in p2.violations
        ]

        _save_rejections(execution, p2_violations)
        _save_quality(execution, CHECKPOINT_P2, p2.counts)

        # Rekaman yang ditolak di P2 tidak boleh ikut skoring. Bukti
        # discrepancy sudah tersimpan di atas (sebelum penghapusan).
        removed_niks = []
        if p2.rejected_respondent_ids:
            removed_niks = sorted(
                Respondent.objects
                .filter(id__in=p2.rejected_respondent_ids)
                .values_list("nik", flat=True)
            )
            Respondent.objects.filter(
                id__in=p2.rejected_respondent_ids
            ).delete()

        execution.n_rejected_p2 = len(p2.rejected_rows)
        execution.n_rejected = (
            execution.n_rejected_p1 + execution.n_rejected_p2
        )
        execution.n_lost = len(p2.lost_rows)
        execution.n_output = len(p2.verified_rows)
        execution.delta_n = execution.n_input - (
            execution.n_output + execution.n_rejected
        )

        # ---- pipeline existing (agregasi skor) -------------------
        n_scored_villages = None
        if run_scoring:
            n_scored_villages = ScoreAggregationService.populate_all()

        execution.output_summary = {
            **execution.output_summary,
            "p2_removed_niks": removed_niks,
            "created_respondent": import_result["created_respondent"],
            "updated_respondent": import_result["updated_respondent"],
            "created_response": import_result["created_response"],
            "skipped_rows": import_result["skipped_rows"][:50],
            "n_skipped_rows": len(import_result["skipped_rows"]),
            "scored_villages": n_scored_villages,
            "database_state": database_state(),
        }

        return _finish(execution, ExecutionLog.STATUS_SUCCESS)
