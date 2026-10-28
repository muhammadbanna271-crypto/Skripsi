from io import BytesIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from apps.master.models import (
    District,
    Indicator,
    Questionnaire,
    Variable,
    Village,
)
from apps.master.services.excel_import_service import (
    DistrictExcelImportService,
    ExcelImportError,
    VariableExcelImportService,
    VillageExcelImportService,
    district_template,
    variable_template,
    village_template,
)

DATA_DIR = Path(__file__).resolve().parents[5] / "Data"


def make_xlsx(rows, name="data.xlsx"):
    workbook = Workbook()
    for row in rows:
        workbook.active.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(name, buffer.getvalue())


VILLAGE_HEADER = ("ID Desa", "Kecamatan", "Desa/Kelurahan")
VARIABLE_HEADER = ("Variabel", None, "Indikator", None, "Pernyataan", "Jenis Jawaban")
DISTRICT_HEADER = ("ID Kecamatan", "Kecamatan")
L = "Skala Likert (1-5)"


class DistrictImportTests(TestCase):
    def test_imports_with_ids_from_file(self):
        result = DistrictExcelImportService.import_file(make_xlsx([
            DISTRICT_HEADER, (1, "Batu"), (2, "Bumiaji"), (None, None),
        ]))
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(District.objects.get(name="Bumiaji").code, "2")
        self.assertEqual(District.objects.count(), 2)

    def test_reimport_idempotent_and_errors(self):
        rows = [DISTRICT_HEADER, (1, "Batu")]
        DistrictExcelImportService.import_file(make_xlsx(rows))
        self.assertTrue(DistrictExcelImportService.import_file(make_xlsx(rows)).ok)
        bad = DistrictExcelImportService.import_file(make_xlsx([
            DISTRICT_HEADER, (1, "Bumiaji"), ("x", "Junrejo"), (3, "Batu"),
        ]))
        self.assertFalse(bad.ok)
        self.assertEqual({r for r, _ in bad.errors}, {2, 3, 4})
        self.assertEqual(District.objects.count(), 1)

    def test_village_import_reuses_imported_district_ids(self):
        DistrictExcelImportService.import_file(make_xlsx([
            DISTRICT_HEADER, (7, "Junrejo"),
        ]))
        VillageExcelImportService.import_file(make_xlsx([
            VILLAGE_HEADER, (1, "Junrejo", "Beji"),
        ]))
        self.assertEqual(District.objects.count(), 1)
        self.assertEqual(Village.objects.get(name="Beji").district.code, "7")


class VillageImportTests(TestCase):
    def test_imports_villages_and_creates_districts(self):
        result = VillageExcelImportService.import_file(make_xlsx([
            VILLAGE_HEADER,
            (1, "Batu", "Oro-oro Ombo"),
            (2, "Batu", "Ngaglik"),
            (9, "Bumiaji", "Bumiaji"),
        ]))
        self.assertTrue(result.ok)
        self.assertEqual(Village.objects.count(), 3)
        self.assertEqual(District.objects.count(), 2)
        self.assertEqual(Village.objects.get(code="9").district.name, "Bumiaji")

    def test_reimport_is_idempotent(self):
        rows = [VILLAGE_HEADER, (1, "Batu", "Ngaglik")]
        VillageExcelImportService.import_file(make_xlsx(rows))
        result = VillageExcelImportService.import_file(make_xlsx(rows))
        self.assertTrue(result.ok)
        self.assertEqual(Village.objects.count(), 1)
        self.assertEqual(District.objects.count(), 1)

    def test_any_error_saves_nothing(self):
        result = VillageExcelImportService.import_file(make_xlsx([
            VILLAGE_HEADER,
            (1, "Batu", "Ngaglik"),
            ("abc", "Batu", "Sisir"),
            (3, "Batu", "Ngaglik"),
        ]))
        self.assertFalse(result.ok)
        self.assertEqual({row for row, _ in result.errors}, {3, 4})
        self.assertEqual(Village.objects.count(), 0)
        self.assertEqual(District.objects.count(), 0)

    def test_conflict_with_existing_village(self):
        district = District.objects.create(code="1", name="Batu")
        Village.objects.create(code="1", name="Ngaglik", district=district)
        result = VillageExcelImportService.import_file(make_xlsx([
            VILLAGE_HEADER, (1, "Batu", "Sisir"),
        ]))
        self.assertFalse(result.ok)

    def test_rejects_non_excel(self):
        with self.assertRaises(ExcelImportError):
            VillageExcelImportService.import_file(
                SimpleUploadedFile("x.xlsx", b"bukan excel")
            )
        with self.assertRaises(ExcelImportError):
            VillageExcelImportService.import_file(
                SimpleUploadedFile("x.csv", b"1,Batu,Ngaglik")
            )


class VariableImportTests(TestCase):
    ROWS = [
        VARIABLE_HEADER,
        ("X1", "Orientasi Pasar", "X1.1", "Kualitas pelayanan", "Pernyataan A", L),
        ("X1", "Orientasi Pasar", "X1.2", "Pemahaman kebutuhan", "Pernyataan B", "Ya/Tidak"),
        ("Y1", "Inovasi", "Y1.1", "Inovasi produk", "Pernyataan C", L),
        ("Z1", "Kunjungan", "Z1.1", "Jumlah kunjungan", "Pernyataan D", "Angka Bulat"),
    ]

    def test_imports_roles_indicators_and_questions(self):
        result = VariableExcelImportService.import_file(make_xlsx(self.ROWS))
        self.assertTrue(result.ok, result.errors)
        roles = {v.name: v.role for v in Variable.objects.all()}
        self.assertEqual(roles["Orientasi Pasar"], Variable.ROLE_PREDICTOR)
        self.assertEqual(roles["Inovasi"], Variable.ROLE_MEDIATOR)
        self.assertEqual(roles["Kunjungan"], Variable.ROLE_RESPONSE)
        self.assertEqual(Variable.objects.get(name="Inovasi").mediator_layer.number, 1)
        self.assertEqual(Indicator.objects.count(), 4)
        self.assertEqual(Questionnaire.objects.count(), 4)
        self.assertEqual(
            set(Indicator.objects.values_list("code", flat=True)),
            {"X1.1", "X1.2", "Y1.1", "Z1.1"},
        )
        types = dict(Questionnaire.objects.values_list("question", "answer_type"))
        self.assertEqual(types["Pernyataan A"], "likert")
        self.assertEqual(types["Pernyataan B"], "boolean")
        self.assertEqual(types["Pernyataan D"], "integer")

    def test_reimport_is_idempotent(self):
        VariableExcelImportService.import_file(make_xlsx(self.ROWS))
        result = VariableExcelImportService.import_file(make_xlsx(self.ROWS))
        self.assertTrue(result.ok)
        self.assertEqual(Variable.objects.count(), 3)
        self.assertEqual(Indicator.objects.count(), 4)
        self.assertEqual(Questionnaire.objects.count(), 4)

    def test_import_into_existing_data_keeps_codes_unique(self):
        VariableExcelImportService.import_file(make_xlsx(self.ROWS))
        # Variabel baru berkode X1 di file, tapi X1 sudah dipakai di sistem.
        result = VariableExcelImportService.import_file(make_xlsx([
            VARIABLE_HEADER,
            ("X1", "Variabel Baru", "X1.1", "Indikator baru", "Pernyataan E", L),
        ]))
        self.assertTrue(result.ok, result.errors)
        codes = list(Variable.objects.values_list("code", flat=True))
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(Variable.objects.get(name="Variabel Baru").code, "X2")
        self.assertEqual(Indicator.objects.get(name="Indikator baru").code, "X2.1")

    def test_validation_errors_save_nothing(self):
        result = VariableExcelImportService.import_file(make_xlsx([
            VARIABLE_HEADER,
            ("X1", "A", "X1.1", "Ind A", "ok", L),
            ("X1", "A", "Y1.1", "Ind B", "kode indikator salah variabel", L),
            ("Q9", "B", "Q9.1", "Ind C", "prefix tidak dikenal", L),
            ("X2", "C", "X2.1", "Ind D", "", "jenis aneh"),
        ]))
        self.assertFalse(result.ok)
        self.assertEqual({row for row, _ in result.errors}, {3, 4, 5})
        self.assertEqual(Variable.objects.count(), 0)
        self.assertEqual(Indicator.objects.count(), 0)

    def test_same_variable_code_with_two_names_is_rejected(self):
        result = VariableExcelImportService.import_file(make_xlsx([
            VARIABLE_HEADER,
            ("X1", "A", "X1.1", "Ind A", "p", L),
            ("X1", "B", "X1.2", "Ind B", "p", L),
        ]))
        self.assertFalse(result.ok)


class ImportViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("admin", password="x", is_staff=True)
        self.user = User.objects.create_user("biasa", password="x")

    def test_pages_and_templates_are_staff_only(self):
        names = [
            "master:district-import", "master:district-import-template",
            "master:village-import", "master:village-import-template",
            "master:variable-import", "master:variable-import-template",
        ]
        self.client.force_login(self.user)
        for name in names:
            self.assertNotEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.client.logout()
        for name in names:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)

        self.client.force_login(self.admin)
        for name in names:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_post_import_via_view(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("master:village-import"),
            {"file": make_xlsx([VILLAGE_HEADER, (1, "Batu", "Ngaglik")])},
        )
        self.assertRedirects(
            response, reverse("master:village-list"), fetch_redirect_response=False
        )
        self.assertEqual(Village.objects.count(), 1)

    def test_post_with_errors_shows_rows(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("master:village-import"),
            {"file": make_xlsx([VILLAGE_HEADER, ("x", "Batu", "Ngaglik")])},
        )
        self.assertContains(response, "Baris 2")
        self.assertEqual(Village.objects.count(), 0)

    def test_templates_are_importable_themselves(self):
        # File contoh harus lolos impornya sendiri.
        for builder, service in (
            (district_template, DistrictExcelImportService),
            (village_template, VillageExcelImportService),
            (variable_template, VariableExcelImportService),
        ):
            buffer = BytesIO()
            builder().save(buffer)
            upload = SimpleUploadedFile("contoh.xlsx", buffer.getvalue())
            self.assertTrue(service.import_file(upload).ok)


class RealDataFileTests(TestCase):
    """Memakai file asli di folder Data bila tersedia."""

    def _upload(self, name):
        path = DATA_DIR / name
        if not path.exists():
            self.skipTest(f"{path} tidak ada")
        return SimpleUploadedFile(name, path.read_bytes())

    def test_kecamatan_trip(self):
        result = DistrictExcelImportService.import_file(
            self._upload("Kecamatan_TRIP.xlsx")
        )
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(
            dict(District.objects.values_list("name", "code")),
            {"Batu": "1", "Bumiaji": "2", "Junrejo": "3"},
        )

    def test_kecamatan_then_desa(self):
        DistrictExcelImportService.import_file(self._upload("Kecamatan_TRIP.xlsx"))
        result = VillageExcelImportService.import_file(self._upload("Desa_TRIP.xlsx"))
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(District.objects.count(), 3)
        self.assertEqual(Village.objects.count(), 24)

    def test_desa_trip(self):
        result = VillageExcelImportService.import_file(self._upload("Desa_TRIP.xlsx"))
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(Village.objects.count(), 24)
        self.assertEqual(District.objects.count(), 3)

    def test_data_variabel(self):
        result = VariableExcelImportService.import_file(self._upload("Data_Variabel.xlsx"))
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(Variable.objects.count(), 11)
        self.assertEqual(Indicator.objects.count(), 88)
        self.assertEqual(Questionnaire.objects.count(), 88)
        self.assertTrue(Indicator.objects.filter(code="Y6.8").exists())
        self.assertEqual(
            set(Questionnaire.objects.values_list("answer_type", flat=True)),
            {"likert"},
        )
