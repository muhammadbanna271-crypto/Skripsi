import json
import os
import tempfile
from unittest import mock

from apps.analytics.models import VillageScore
from apps.dataquality.fingerprint import database_state
from apps.dataquality.injection import DEFECT_TYPES, inject
from apps.dataquality.models import ExecutionLog, QualityScore, RejectionLog
from apps.dataquality.pipeline import ValidatedImportService
from apps.respondent.models import Respondent
from apps.response.models import Response
from apps.response.services.bulk_import_service import (
    ResponseBulkImportService,
)

from .helpers import (
    COL_DESA,
    COL_ID,
    COL_PERSON,
    COL_RT,
    FIRST_INDICATOR_COL,
    INDICATOR_CODES,
    N_ROWS,
    DQTestCase,
    make_workbook,
)

N_IND = len(INDICATOR_CODES)


def set_cell(row, col, value):
    def mutate(ws):
        ws.cell(row=row, column=col).value = value
    return mutate


class ValidatedImportTests(DQTestCase):

    def run_import(self, data, **kwargs):
        return ValidatedImportService.run(data, self.survey, **kwargs)

    def rejections(self, execution, **filters):
        return list(execution.rejections.filter(**filters))

    # ---- schema gate -------------------------------------------
    def test_complete_schema_passes(self):
        execution = self.run_import(make_workbook())

        self.assertEqual(execution.status, ExecutionLog.STATUS_SUCCESS)
        self.assertEqual(execution.n_input, N_ROWS)
        self.assertEqual(execution.n_accepted, N_ROWS)
        self.assertEqual(execution.n_rejected, 0)
        self.assertEqual(execution.n_output, N_ROWS)
        self.assertEqual(execution.delta_n, 0)
        self.assertEqual(Respondent.objects.count(), N_ROWS)
        self.assertEqual(Response.objects.count(), N_ROWS * N_IND)

    def test_missing_indicator_column_detected(self):
        def drop(ws):
            ws.delete_cols(FIRST_INDICATOR_COL + 3)

        execution = self.run_import(make_workbook(drop))

        self.assertEqual(execution.status, ExecutionLog.STATUS_FAILED_SCHEMA)
        self.assertIn(INDICATOR_CODES[3], execution.error_message)
        self.assertEqual(Respondent.objects.count(), 0)
        self.assertEqual(Response.objects.count(), 0)
        self.assertEqual(execution.quality_scores.count(), 0)

    def test_missing_identity_column_detected(self):
        def drop(ws):
            ws.delete_cols(COL_RT)

        execution = self.run_import(make_workbook(drop))

        self.assertEqual(execution.status, ExecutionLog.STATUS_FAILED_SCHEMA)
        self.assertEqual(Respondent.objects.count(), 0)

    def test_blank_column_is_completeness_not_schema(self):
        def blank(ws):
            for r in range(2, ws.max_row + 1):
                ws.cell(row=r, column=FIRST_INDICATOR_COL).value = None

        execution = self.run_import(make_workbook(blank))

        self.assertEqual(execution.status, ExecutionLog.STATUS_SUCCESS)
        self.assertEqual(execution.n_rejected_p1, N_ROWS)
        self.assertEqual(execution.n_output, 0)

    # ---- empat dimensi -----------------------------------------
    def test_empty_cell_is_completeness(self):
        execution = self.run_import(
            make_workbook(set_cell(5, FIRST_INDICATOR_COL + 2, None))
        )

        logs = self.rejections(execution, checkpoint="P1")
        self.assertEqual(len(logs), 1)
        log = logs[0]
        self.assertEqual(log.dimension, "completeness")
        self.assertEqual(log.source_row, 5)
        self.assertEqual(log.column_name, INDICATOR_CODES[2])
        self.assertEqual(log.respondent_id, "4")
        self.assertEqual(execution.n_rejected_p1, 1)
        self.assertEqual(execution.n_output, N_ROWS - 1)

    def test_text_indicator_is_validity(self):
        execution = self.run_import(
            make_workbook(set_cell(3, FIRST_INDICATOR_COL, "3"))
        )

        log = self.rejections(execution, checkpoint="P1")[0]
        self.assertEqual(log.dimension, "validity")
        self.assertEqual(log.original_value, "3")
        self.assertEqual(log.value_type, "str")
        self.assertEqual(execution.n_rejected_p1, 1)

    def test_out_of_range_and_non_integer_are_validity(self):
        for value in (0, 6, -1, 3.5):
            with self.subTest(value=value):
                Respondent.objects.all().delete()
                execution = self.run_import(
                    make_workbook(set_cell(3, FIRST_INDICATOR_COL, value))
                )
                log = self.rejections(execution, checkpoint="P1")[0]
                self.assertEqual(log.dimension, "validity")
                self.assertEqual(execution.n_rejected_p1, 1)

    def test_unknown_village_is_consistency(self):
        execution = self.run_import(make_workbook(set_cell(4, COL_DESA, 999)))

        logs = self.rejections(execution, checkpoint="P1")
        self.assertEqual([l.dimension for l in logs], ["consistency"])
        self.assertEqual(logs[0].column_name, "Desa")
        self.assertEqual(execution.n_rejected_p1, 1)

    def test_duplicate_id_resp_is_uniqueness(self):
        # Baris 10 memakai ID Resp baris 3; baris 3 (pertama) tetap diterima.
        execution = self.run_import(make_workbook(set_cell(10, COL_ID, 2)))

        logs = self.rejections(execution, checkpoint="P1")
        self.assertEqual([l.dimension for l in logs], ["uniqueness"])
        self.assertEqual(logs[0].source_row, 10)
        self.assertEqual(logs[0].rule, "id_resp_duplicate")
        self.assertEqual(execution.n_rejected_p1, 1)
        self.assertTrue(Respondent.objects.filter(nik="IMPORT-2").exists())

    def test_duplicate_combo_is_uniqueness(self):
        def mutate(ws):
            for col in (COL_DESA, COL_RT, COL_PERSON):
                ws.cell(row=10, column=col).value = ws.cell(
                    row=3, column=col
                ).value

        execution = self.run_import(make_workbook(mutate))

        logs = self.rejections(execution, checkpoint="P1")
        self.assertEqual([l.rule for l in logs], ["desa_rt_person_duplicate"])
        self.assertEqual(logs[0].dimension, "uniqueness")
        self.assertEqual(logs[0].source_row, 10)

    def test_multiple_violations_in_one_row_all_logged(self):
        def mutate(ws):
            ws.cell(row=3, column=FIRST_INDICATOR_COL).value = None
            ws.cell(row=3, column=FIRST_INDICATOR_COL + 1).value = 9
            ws.cell(row=3, column=COL_DESA).value = 999

        execution = self.run_import(make_workbook(mutate))

        dims = sorted(l.dimension for l in self.rejections(execution))
        self.assertEqual(dims, ["completeness", "consistency", "validity"])
        self.assertEqual(execution.n_rejected_p1, 1)

    # ---- accept/reject & pipeline existing ---------------------
    def test_rejected_rows_never_reach_scoring(self):
        execution = self.run_import(
            make_workbook(set_cell(5, FIRST_INDICATOR_COL, 9))
        )

        self.assertFalse(Respondent.objects.filter(nik="IMPORT-4").exists())
        self.assertFalse(
            Response.objects.filter(respondent__nik="IMPORT-4").exists()
        )
        self.assertEqual(Response.objects.count(), (N_ROWS - 1) * N_IND)
        self.assertEqual(execution.n_rejected, 1)

    def test_valid_data_still_processed_by_existing_pipeline(self):
        execution = self.run_import(make_workbook())

        self.assertEqual(VillageScore.objects.count(), 6)
        self.assertEqual(execution.output_summary["scored_villages"], 6)

    def test_valid_rows_processed_when_other_rows_rejected(self):
        execution = self.run_import(
            make_workbook(set_cell(5, FIRST_INDICATOR_COL, "x"))
        )

        self.assertEqual(execution.status, ExecutionLog.STATUS_SUCCESS)
        self.assertEqual(execution.n_output, N_ROWS - 1)
        self.assertEqual(VillageScore.objects.count(), 6)

    # ---- logs & skor kualitas ----------------------------------
    def test_execution_log_created(self):
        data = make_workbook()
        execution = self.run_import(data)

        fresh = ExecutionLog.objects.get(execution_id=execution.execution_id)
        self.assertEqual(len(fresh.source_sha256), 64)
        self.assertEqual(fresh.rules_version, "1.0.0")
        self.assertIsNotNone(fresh.started_at)
        self.assertIsNotNone(fresh.finished_at)
        self.assertEqual(fresh.survey, self.survey)

    def test_same_file_same_hash(self):
        data = make_workbook()
        a = self.run_import(data)
        b = self.run_import(data)
        self.assertEqual(a.source_sha256, b.source_sha256)
        self.assertNotEqual(a.execution_id, b.execution_id)

    def test_rejection_log_has_required_fields(self):
        execution = self.run_import(
            make_workbook(set_cell(3, FIRST_INDICATOR_COL, 6))
        )

        log = RejectionLog.objects.get(execution=execution)
        self.assertEqual(log.execution_id, execution.id)
        self.assertEqual(log.respondent_id, "2")
        self.assertEqual(log.source_row, 3)
        self.assertEqual(log.column_name, INDICATOR_CODES[0])
        self.assertEqual(log.original_value, "6")
        self.assertEqual(log.dimension, "validity")
        self.assertEqual(log.rule, "indicator_range")
        self.assertEqual(log.checkpoint, "P1")
        self.assertTrue(log.reason)

    def test_quality_scores_for_p1_and_p2(self):
        execution = self.run_import(make_workbook())

        scores = {
            (q.checkpoint, q.dimension): q
            for q in QualityScore.objects.filter(execution=execution)
        }
        self.assertEqual(len(scores), 8)
        for q in scores.values():
            self.assertEqual(q.score, 1.0)

        cells = N_ROWS * (4 + N_IND)
        self.assertEqual(scores[("P1", "completeness")].n_checked, cells)
        self.assertEqual(scores[("P1", "validity")].n_checked, cells)
        self.assertEqual(scores[("P1", "consistency")].n_checked, N_ROWS)
        self.assertEqual(scores[("P1", "uniqueness")].n_checked, N_ROWS)
        self.assertEqual(scores[("P2", "completeness")].n_checked, cells)

    def test_quality_score_formula(self):
        execution = self.run_import(
            make_workbook(set_cell(5, FIRST_INDICATOR_COL, None))
        )

        q = QualityScore.objects.get(
            execution=execution, checkpoint="P1", dimension="completeness"
        )
        cells = N_ROWS * (4 + N_IND)
        self.assertEqual(q.n_satisfied, cells - 1)
        self.assertAlmostEqual(q.score, (cells - 1) / cells)

        # Sel kosong tidak dihitung ganda sebagai invalid.
        v = QualityScore.objects.get(
            execution=execution, checkpoint="P1", dimension="validity"
        )
        self.assertEqual(v.n_checked, cells - 1)
        self.assertEqual(v.score, 1.0)

    # ---- rekonsiliasi & P2 -------------------------------------
    def test_reconciliation_with_rejections(self):
        def mutate(ws):
            ws.cell(row=3, column=FIRST_INDICATOR_COL).value = None
            ws.cell(row=4, column=COL_DESA).value = 999
            ws.cell(row=10, column=COL_ID).value = 2

        execution = self.run_import(make_workbook(mutate))

        self.assertEqual(execution.n_input, N_ROWS)
        self.assertEqual(execution.n_rejected, 3)
        self.assertEqual(execution.n_output, N_ROWS - 3)
        self.assertEqual(execution.delta_n, 0)

    def test_p2_detects_lost_record(self):
        original = ResponseBulkImportService._import_answers

        def flaky(respondent, row_dict, questionnaire_map):
            if respondent.nik == "IMPORT-7":
                raise RuntimeError("gagal simpan")
            return original(respondent, row_dict, questionnaire_map)

        with mock.patch.object(
            ResponseBulkImportService, "_import_answers", staticmethod(flaky)
        ):
            execution = self.run_import(make_workbook())

        self.assertEqual(execution.n_lost, 1)
        self.assertEqual(execution.delta_n, 1)
        self.assertEqual(execution.n_output, N_ROWS - 1)
        log = execution.rejections.get(checkpoint="P2")
        self.assertEqual(log.rule, "record_not_stored")
        self.assertEqual(log.respondent_id, "7")
        q = QualityScore.objects.get(
            execution=execution, checkpoint="P2", dimension="uniqueness"
        )
        self.assertLess(q.score, 1.0)

    def test_p2_rejects_and_removes_record_with_wrong_stored_value(self):
        original = ResponseBulkImportService._import_answers

        def corrupt(respondent, row_dict, questionnaire_map):
            if respondent.nik == "IMPORT-7":
                row_dict = dict(row_dict)
                row_dict[INDICATOR_CODES[0].lower()] = (
                    1 if row_dict[INDICATOR_CODES[0].lower()] != 1 else 2
                )
            return original(respondent, row_dict, questionnaire_map)

        with mock.patch.object(
            ResponseBulkImportService, "_import_answers", staticmethod(corrupt)
        ):
            execution = self.run_import(make_workbook())

        self.assertEqual(execution.n_rejected_p2, 1)
        self.assertEqual(execution.n_lost, 0)
        self.assertEqual(execution.delta_n, 0)
        self.assertFalse(Respondent.objects.filter(nik="IMPORT-7").exists())
        log = execution.rejections.get(checkpoint="P2")
        self.assertEqual(log.dimension, "consistency")
        self.assertEqual(log.rule, "stored_value_mismatch")

    # ---- determinisme & idempotensi ----------------------------
    def test_same_input_same_output(self):
        data = make_workbook()

        self.run_import(data)
        first = database_state()

        Respondent.objects.all().delete()
        VillageScore.objects.all().delete()
        self.assertEqual(Response.objects.count(), 0)

        self.run_import(data)

        self.assertEqual(database_state(), first)

    def test_upload_twice_same_final_state(self):
        data = make_workbook()

        first = self.run_import(data)
        state_1 = database_state()

        second = self.run_import(data)
        state_2 = database_state()

        self.assertEqual(state_1, state_2)
        self.assertEqual(first.output_summary["created_respondent"], N_ROWS)
        self.assertEqual(second.output_summary["created_respondent"], 0)
        self.assertEqual(second.output_summary["updated_respondent"], N_ROWS)
        self.assertEqual(Respondent.objects.count(), N_ROWS)
        self.assertEqual(Response.objects.count(), N_ROWS * N_IND)


class InjectionTests(DQTestCase):
    """Injeksi satu jenis cacat -> deteksi cocok dengan ground truth."""

    def inject_and_run(self, defect, **kwargs):
        tmp = tempfile.mkdtemp()
        src = os.path.join(tmp, "clean.xlsx")
        out = os.path.join(tmp, "defect.xlsx")
        truth_path = os.path.join(tmp, "truth.json")
        with open(src, "wb") as handle:
            handle.write(make_workbook())

        truth = inject(
            src, out, truth_path, defect,
            seed=42, known_village_codes=[str(i) for i in range(1, 7)],
            **kwargs,
        )
        execution = ValidatedImportService.run(out, self.survey)
        return truth, execution

    def detected(self, execution):
        return {
            (l.source_row, l.column_name)
            for l in execution.rejections.filter(checkpoint="P1")
        }

    def expected(self, truth):
        return {(r["row"], r["column"]) for r in truth["records"]}

    def test_missing_value(self):
        truth, ex = self.inject_and_run("missing_value", count=8)
        self.assertEqual(self.detected(ex), self.expected(truth))
        self.assertEqual(
            {l.dimension for l in ex.rejections.all()}, {"completeness"}
        )

    def test_wrong_type(self):
        truth, ex = self.inject_and_run("wrong_type", count=8)
        self.assertEqual(self.detected(ex), self.expected(truth))
        self.assertEqual(
            {l.dimension for l in ex.rejections.all()}, {"validity"}
        )

    def test_out_of_range(self):
        truth, ex = self.inject_and_run("out_of_range", count=8)
        self.assertEqual(self.detected(ex), self.expected(truth))
        self.assertEqual(
            {l.dimension for l in ex.rejections.all()}, {"validity"}
        )

    def test_duplicate_row(self):
        truth, ex = self.inject_and_run("duplicate", count=5, variant="row")
        self.assertEqual(
            {l.source_row for l in ex.rejections.all()},
            {r["row"] for r in truth["records"]},
        )
        self.assertEqual(
            {l.dimension for l in ex.rejections.all()}, {"uniqueness"}
        )
        self.assertEqual(ex.delta_n, 0)

    def test_duplicate_id(self):
        truth, ex = self.inject_and_run("duplicate", count=5, variant="id")
        self.assertEqual(self.detected(ex), self.expected(truth))
        self.assertEqual({l.rule for l in ex.rejections.all()},
                         {"id_resp_duplicate"})

    def test_duplicate_combo(self):
        truth, ex = self.inject_and_run("duplicate", count=5, variant="combo")
        self.assertEqual(self.detected(ex), self.expected(truth))
        self.assertEqual({l.rule for l in ex.rejections.all()},
                         {"desa_rt_person_duplicate"})

    def test_missing_column_drop_is_schema_failure(self):
        truth, ex = self.inject_and_run("missing_column", variant="drop",
                                        count=2)
        self.assertEqual(ex.status, ExecutionLog.STATUS_FAILED_SCHEMA)
        for record in truth["records"]:
            self.assertIn(record["column"], ex.error_message)

    def test_missing_column_blank_is_completeness(self):
        truth, ex = self.inject_and_run("missing_column", variant="blank",
                                        count=1)
        self.assertEqual(self.detected(ex), self.expected(truth))
        self.assertEqual(
            {l.dimension for l in ex.rejections.all()}, {"completeness"}
        )

    def test_unknown_village(self):
        truth, ex = self.inject_and_run("unknown_village", count=4)
        self.assertEqual(self.detected(ex), self.expected(truth))
        self.assertEqual(
            {l.dimension for l in ex.rejections.all()}, {"consistency"}
        )

    def test_same_seed_same_ground_truth(self):
        a, _ = self.inject_and_run("missing_value", count=6)
        b, _ = self.inject_and_run("missing_value", count=6)
        self.assertEqual(a["records"], b["records"])
        self.assertEqual(a["seed"], 42)

    def test_ground_truth_fields_and_defect_types(self):
        truth, _ = self.inject_and_run("wrong_type", count=3)
        self.assertEqual(set(DEFECT_TYPES) >= {truth["defect_type"]}, True)
        for record in truth["records"]:
            self.assertEqual(
                set(record),
                {"respondent_id", "row", "column", "defect_type",
                 "original_value", "injected_value"},
            )
        self.assertIsInstance(json.dumps(truth, default=str), str)


class ImportViewTests(DQTestCase):

    def test_view_runs_validated_import(self):
        from django.contrib.auth import get_user_model
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.urls import reverse

        user = get_user_model().objects.create_user(
            "staff", password="x", is_staff=True
        )
        self.client.force_login(user)

        upload = SimpleUploadedFile(
            "survei.xlsx",
            make_workbook(set_cell(5, FIRST_INDICATOR_COL, 9)),
        )
        response = self.client.post(
            reverse("response:response-import"),
            {"survey_id": self.survey.pk, "excel_file": upload},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        execution = ExecutionLog.objects.get()
        self.assertEqual(execution.source_filename, "survei.xlsx")
        self.assertEqual(execution.n_rejected, 1)
        self.assertEqual(Respondent.objects.count(), N_ROWS - 1)
