import csv
import os
import tempfile
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.dataquality.evaluation import compare_executions, evaluate
from apps.dataquality.injection import inject, write_clean
from apps.dataquality.pipeline import ValidatedImportService
from apps.dataquality.reporting import export_execution
from apps.respondent.models import Respondent
from apps.response.services.bulk_import_service import (
    ResponseBulkImportService,
)

from .helpers import (
    COL_DESA,
    COL_ID,
    FIRST_INDICATOR_COL,
    INDICATOR_CODES,
    N_ROWS,
    DQTestCase,
    make_workbook,
)

EXPECTED_FILES = {
    "execution_summary.csv", "rejection_detail.csv",
    "discrepancy_detail.csv", "quality_score.csv", "fingerprints.txt",
    "report.txt",
}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def set_cell(row, col, value):
    def mutate(ws):
        ws.cell(row=row, column=col).value = value
    return mutate


class ReportingTests(DQTestCase):

    def setUp(self):
        super().setUp()
        self.out = tempfile.mkdtemp()

    def run_import(self, data, **kwargs):
        return ValidatedImportService.run(data, self.survey, **kwargs)

    def export(self, execution, **kwargs):
        return export_execution(execution, self.out, **kwargs)

    def path(self, name):
        return os.path.join(self.out, name)

    # ---- command -----------------------------------------------
    def test_dq_report_command_writes_all_files(self):
        execution = self.run_import(make_workbook())

        stdout = StringIO()
        call_command(
            "dq_report", execution.execution_id, output=self.out,
            stdout=stdout,
        )

        self.assertTrue(EXPECTED_FILES <= set(os.listdir(self.out)))
        self.assertIn(execution.execution_id, stdout.getvalue())

    def test_dq_report_latest_and_errors(self):
        self.run_import(make_workbook())
        last = self.run_import(make_workbook())

        call_command("dq_report", latest=True, output=self.out,
                     stdout=StringIO())
        rows = read_csv(self.path("execution_summary.csv"))
        self.assertEqual(rows[0]["execution_id"], last.execution_id)

        with self.assertRaises(CommandError):
            call_command("dq_report", output=self.out)
        with self.assertRaises(CommandError):
            call_command("dq_report", "tidak-ada", output=self.out)

    def test_export_specific_execution_does_not_include_other(self):
        first = self.run_import(
            make_workbook(set_cell(3, FIRST_INDICATOR_COL, 9))
        )
        second = self.run_import(make_workbook())

        self.export(first)

        summary = read_csv(self.path("execution_summary.csv"))
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["execution_id"], first.execution_id)
        for table in ("rejection_detail", "quality_score"):
            ids = {r["execution_id"]
                   for r in read_csv(self.path(f"{table}.csv"))}
            self.assertEqual(ids, {first.execution_id})
            self.assertNotIn(second.execution_id, ids)

    # ---- isi file ----------------------------------------------
    def test_execution_summary_values(self):
        execution = self.run_import(
            make_workbook(set_cell(3, FIRST_INDICATOR_COL, 9))
        )
        self.export(execution)

        row = read_csv(self.path("execution_summary.csv"))[0]
        self.assertEqual(row["status"], "success")
        self.assertEqual(row["n_input"], str(N_ROWS))
        self.assertEqual(row["n_accepted"], str(N_ROWS - 1))
        self.assertEqual(row["n_rejected"], "1")
        self.assertEqual(row["n_output"], str(N_ROWS - 1))
        self.assertEqual(row["n_lost"], "0")
        self.assertEqual(row["delta_n"], "0")
        self.assertEqual(row["source_sha256"], execution.source_sha256)
        self.assertEqual(row["rules_version"], "1.0.0")
        self.assertTrue(row["started_at"] and row["finished_at"])

    def test_rejection_detail_shows_every_violation(self):
        def mutate(ws):
            ws.cell(row=3, column=FIRST_INDICATOR_COL).value = None
            ws.cell(row=3, column=FIRST_INDICATOR_COL + 1).value = "3"
            ws.cell(row=3, column=COL_DESA).value = 999

        execution = self.run_import(make_workbook(mutate))
        self.export(execution)

        rows = read_csv(self.path("rejection_detail.csv"))
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            {r["dimension"] for r in rows},
            {"completeness", "validity", "consistency"},
        )
        validity = next(r for r in rows if r["dimension"] == "validity")
        self.assertEqual(validity["original_value"], "3")
        self.assertEqual(validity["value_type"], "str")
        self.assertEqual(validity["id_resp"], "2")
        self.assertEqual(validity["source_row"], "3")
        self.assertEqual(validity["checkpoint"], "P1")
        self.assertEqual(validity["column_name"], INDICATOR_CODES[1])

    def test_quality_score_csv(self):
        execution = self.run_import(
            make_workbook(set_cell(3, FIRST_INDICATOR_COL, None))
        )
        self.export(execution)

        rows = read_csv(self.path("quality_score.csv"))
        self.assertEqual(len(rows), 8)
        self.assertEqual(
            [r["dimension"] for r in rows[:4]],
            ["completeness", "validity", "consistency", "uniqueness"],
        )
        p1c = next(r for r in rows
                   if r["checkpoint"] == "P1"
                   and r["dimension"] == "completeness")
        self.assertAlmostEqual(
            float(p1c["score"]),
            int(p1c["n_satisfied"]) / int(p1c["n_checked"]),
        )

    def test_null_score_exported_as_not_computable(self):
        # Semua baris ditolak -> P2 tidak punya objek pemeriksaan.
        def blank(ws):
            for r in range(2, ws.max_row + 1):
                ws.cell(row=r, column=FIRST_INDICATOR_COL).value = None

        execution = self.run_import(make_workbook(blank))
        self.export(execution)

        rows = read_csv(self.path("quality_score.csv"))
        p2 = [r for r in rows if r["checkpoint"] == "P2"]
        self.assertTrue(all(r["score"] == "" for r in p2))
        self.assertTrue(all("tidak dapat dihitung" in r["note"] for r in p2))

    def test_fingerprints_separate_and_timestamp_free(self):
        execution = self.run_import(make_workbook())
        self.export(execution)

        text = read_text(self.path("fingerprints.txt"))
        for label in ("[RESPONDEN]", "[JAWABAN]", "[SKOR]"):
            self.assertIn(label, text)
        state = execution.output_summary["database_state"]
        for key in ("respondents_sha256", "answers_sha256", "scores_sha256"):
            self.assertIn(state[key], text)

    def test_report_txt_sections(self):
        execution = self.run_import(
            make_workbook(set_cell(3, FIRST_INDICATOR_COL, 9))
        )
        self.export(execution)

        text = read_text(self.path("report.txt"))
        for section in ("EXECUTION", "P1 QUALITY", "P2 QUALITY",
                        "REJECTION SUMMARY", "RECONCILIATION", "FINGERPRINT",
                        "P2 DISCREPANCY", "UNIQUENESS DETAIL"):
            self.assertIn(section, text)
        self.assertIn(execution.execution_id, text)
        self.assertIn("cocok", text)

    # ---- Person ------------------------------------------------
    def test_report_states_person_rule_inactive(self):
        execution = self.run_import(make_workbook())
        self.export(execution)

        text = read_text(self.path("report.txt"))
        self.assertIn("TIDAK AKTIF", text)
        self.assertIn("BELUM diuji", text)
        row = read_csv(self.path("execution_summary.csv"))[0]
        self.assertEqual(row["person_domain_rule"], "inactive")

    @override_settings(DATAQUALITY_ALLOWED_PERSONS=["Kades", "Sekdes"])
    def test_person_rule_active_is_visible_and_enforced(self):
        execution = self.run_import(make_workbook())
        self.export(execution)

        config = execution.output_summary["config"]
        self.assertEqual(config["person_domain_rule"], "active")
        self.assertEqual(config["allowed_persons"], ["kades", "sekdes"])
        self.assertIn("AKTIF", read_text(self.path("report.txt")))
        self.assertTrue(
            execution.rejections.filter(rule="person_domain").exists()
        )

    # ---- schema gate -------------------------------------------
    def test_schema_failure_is_exportable_without_scores(self):
        def drop(ws):
            ws.delete_cols(FIRST_INDICATOR_COL + 3)

        execution = self.run_import(make_workbook(drop))
        self.export(execution)

        summary = read_csv(self.path("execution_summary.csv"))[0]
        self.assertEqual(summary["status"], "failed_schema")
        self.assertEqual(summary["delta_n"], "")
        self.assertIn(INDICATOR_CODES[3], summary["error_message"])
        self.assertEqual(read_csv(self.path("quality_score.csv")), [])
        text = read_text(self.path("report.txt"))
        self.assertIn("SCHEMA GATE", text)
        self.assertIn("GAGAL", text)
        self.assertIn(INDICATOR_CODES[3], text)
        self.assertNotIn("P1 QUALITY", text)

    # ---- uniqueness traceability --------------------------------
    def test_duplicate_shows_first_occurrence(self):
        execution = self.run_import(make_workbook(set_cell(10, COL_ID, 2)))
        self.export(execution)

        row = read_csv(self.path("rejection_detail.csv"))[0]
        self.assertEqual(row["source_row"], "10")
        self.assertEqual(row["related_row"], "3")
        self.assertIn("baris 3", row["reason"])
        self.assertIn(
            "kemunculan pertama dipertahankan pada baris 3",
            read_text(self.path("report.txt")),
        )

    # ---- discrepancy P2 ----------------------------------------
    def test_p2_discrepancy_keeps_source_and_db_values(self):
        original = ResponseBulkImportService._import_answers

        def corrupt(respondent, row_dict, questionnaire_map):
            if respondent.nik == "IMPORT-7":
                row_dict = dict(row_dict)
                key = INDICATOR_CODES[0].lower()
                row_dict[key] = 1 if row_dict[key] != 1 else 2
            return original(respondent, row_dict, questionnaire_map)

        with mock.patch.object(
            ResponseBulkImportService, "_import_answers", staticmethod(corrupt)
        ):
            execution = self.run_import(make_workbook())

        # Rekaman dikeluarkan dari tabel skoring, tetapi bukti tetap ada.
        self.assertFalse(Respondent.objects.filter(nik="IMPORT-7").exists())
        self.assertEqual(execution.output_summary["p2_removed_niks"],
                         ["IMPORT-7"])

        self.export(execution)
        rows = read_csv(self.path("discrepancy_detail.csv"))
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["checkpoint"], "P2")
        self.assertEqual(r["id_resp"], "7")
        self.assertEqual(r["column_name"], INDICATOR_CODES[0])
        self.assertNotEqual(r["original_value"], r["db_value"])
        self.assertTrue(r["db_value"])
        self.assertEqual(r["record_action"], "removed_from_scoring_tables")
        self.assertIn("IMPORT-7", read_text(self.path("report.txt")))

    def test_lost_record_reported_separately_from_rejections(self):
        original = ResponseBulkImportService._import_answers

        def flaky(respondent, row_dict, questionnaire_map):
            if respondent.nik == "IMPORT-7":
                raise RuntimeError("gagal simpan")
            return original(respondent, row_dict, questionnaire_map)

        with mock.patch.object(
            ResponseBulkImportService, "_import_answers", staticmethod(flaky)
        ):
            execution = self.run_import(make_workbook())
        self.export(execution)

        row = read_csv(self.path("execution_summary.csv"))[0]
        self.assertEqual(row["n_lost"], "1")
        self.assertEqual(row["n_rejected"], "0")
        self.assertEqual(row["delta_n"], "1")
        d = read_csv(self.path("discrepancy_detail.csv"))[0]
        self.assertEqual(d["record_action"], "not_stored")
        self.assertEqual(d["db_value"], "<tidak ada>")
        self.assertIn("N_lost", read_text(self.path("report.txt")))


class EvaluationTests(DQTestCase):

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self.src = os.path.join(self.tmp, "clean.xlsx")
        with open(self.src, "wb") as handle:
            handle.write(make_workbook())

    def scenario(self, defect, **kwargs):
        out = os.path.join(self.tmp, f"{defect}.xlsx")
        truth_path = os.path.join(self.tmp, f"{defect}.json")
        truth = inject(
            self.src, out, truth_path, defect, seed=11,
            known_village_codes=[str(i) for i in range(1, 7)], **kwargs,
        )
        execution = ValidatedImportService.run(
            out, self.survey, ground_truth=truth
        )
        return truth, execution

    def test_ground_truth_csv_and_precision_recall(self):
        truth, execution = self.scenario("missing_value", count=6)
        out = os.path.join(self.tmp, "export")
        export_execution(execution, out)

        gt = read_csv(os.path.join(out, "ground_truth.csv"))
        self.assertEqual(len(gt), 6)
        self.assertEqual(
            set(gt[0]),
            {"scenario", "seed", "source_row", "id_resp", "column_name",
             "defect_type", "original_value", "injected_value"},
        )
        self.assertEqual(gt[0]["seed"], "11")

        ev = read_csv(os.path.join(out, "evaluation.csv"))[0]
        self.assertEqual((ev["tp"], ev["fp"], ev["fn"]), ("6", "0", "0"))
        self.assertEqual(float(ev["precision"]), 1.0)
        self.assertEqual(float(ev["recall"]), 1.0)

        # Ground truth dapat dicocokkan dengan rejection_detail.csv
        detected = {
            (r["source_row"], r["column_name"])
            for r in read_csv(os.path.join(out, "rejection_detail.csv"))
        }
        expected = {(r["source_row"], r["column_name"]) for r in gt}
        self.assertEqual(detected, expected)

    def test_all_scenarios_perfect_detection(self):
        cases = [
            ("missing_value", {"count": 5}),
            ("wrong_type", {"count": 5}),
            ("out_of_range", {"count": 5}),
            ("duplicate", {"count": 4, "variant": "row"}),
            ("duplicate", {"count": 4, "variant": "id"}),
            ("duplicate", {"count": 4, "variant": "combo"}),
            ("missing_column", {"count": 2, "variant": "drop"}),
            ("missing_column", {"count": 1, "variant": "blank"}),
            ("unknown_village", {"count": 4}),
        ]
        for defect, kwargs in cases:
            with self.subTest(defect=defect, **kwargs):
                truth, execution = self.scenario(defect, **kwargs)
                ev = evaluate(execution, truth)
                self.assertEqual(ev["fp"], 0, ev)
                self.assertEqual(ev["fn"], 0, ev)
                self.assertEqual(ev["tp"], len(truth["records"]))
                self.assertGreater(ev["tp"], 0)

    def test_duplicate_row_counts_one_defect_per_row(self):
        # Baris duplikat melanggar ID Resp DAN Desa+RT+Person (2 rule),
        # tetapi tetap 1 cacat pada evaluasi.
        truth, execution = self.scenario("duplicate", count=4, variant="row")
        self.assertGreater(execution.rejections.count(), 4)
        ev = evaluate(execution, truth)
        self.assertEqual((ev["tp"], ev["fp"], ev["fn"]), (4, 0, 0))

    def test_false_negative_and_false_positive_are_counted(self):
        truth, execution = self.scenario("missing_value", count=4)
        # Hapus satu ground truth (jadi FP) dan tambah lokasi palsu (FN).
        extra = dict(truth["records"][0], row=999)
        fake = dict(truth, records=truth["records"][1:] + [extra])
        ev = evaluate(execution, fake)
        self.assertEqual((ev["tp"], ev["fp"], ev["fn"]), (3, 1, 1))
        self.assertAlmostEqual(ev["precision"], 3 / 4)
        self.assertAlmostEqual(ev["recall"], 3 / 4)

    def test_clean_dataset_reports_false_positives_only(self):
        out = os.path.join(self.tmp, "control.xlsx")
        truth = write_clean(self.src, out, os.path.join(self.tmp, "c.json"))
        execution = ValidatedImportService.run(
            out, self.survey, ground_truth=truth
        )
        ev = evaluate(execution, truth)
        self.assertEqual((ev["tp"], ev["fp"], ev["fn"]), (0, 0, 0))
        self.assertIsNone(ev["recall"])
        self.assertEqual(execution.n_rejected, 0)

        export_execution(execution, os.path.join(self.tmp, "x"))
        self.assertIn(
            "dataset bersih",
            read_text(os.path.join(self.tmp, "x", "report.txt")),
        )


class ComparisonTests(DQTestCase):

    def test_idempotency_comparison_same(self):
        data = make_workbook()
        a = ValidatedImportService.run(data, self.survey)
        b = ValidatedImportService.run(data, self.survey)

        result = compare_executions(a, b)
        self.assertTrue(result["context"]["same_source_sha256"])
        self.assertTrue(result["all_same"])

        out = tempfile.mkdtemp()
        export_execution(b, out, compare_with=a)
        self.assertIn(
            "HASIL: SAMA", read_text(os.path.join(out, "comparison.txt"))
        )
        self.assertIn("COMPARISON", read_text(os.path.join(out, "report.txt")))

    def test_different_state_is_reported_different(self):
        a = ValidatedImportService.run(make_workbook(), self.survey)
        def change_valid_value(ws):
            cell = ws.cell(row=3, column=FIRST_INDICATOR_COL)
            cell.value = cell.value % 5 + 1  # tetap 1-5, tetapi berbeda

        b = ValidatedImportService.run(
            make_workbook(change_valid_value), self.survey
        )
        result = compare_executions(a, b)
        self.assertFalse(result["context"]["same_source_sha256"])
        self.assertFalse(result["all_same"])

    def test_schema_failure_not_comparable(self):
        ok = ValidatedImportService.run(make_workbook(), self.survey)

        def drop(ws):
            ws.delete_cols(FIRST_INDICATOR_COL)

        bad = ValidatedImportService.run(make_workbook(drop), self.survey)
        self.assertFalse(compare_executions(ok, bad)["comparable"])
