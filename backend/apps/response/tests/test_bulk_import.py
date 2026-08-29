from openpyxl import Workbook
from django.test import TestCase

from apps.master.models import (
    District,
    Indicator,
    Questionnaire,
    Variable,
    Village,
)
from apps.response.services.bulk_import_service import (
    BulkImportError,
    ResponseBulkImportService,
)


class ResponseBulkImportServiceTest(TestCase):

    def setUp(self):
        District.objects.all().delete()
        Village.objects.all().delete()
        Variable.objects.all().delete()
        Indicator.objects.all().delete()
        Questionnaire.objects.all().delete()

    def _district(self):
        return District.objects.create(code="D1", name="Dist 1")

    def test_resolve_village_by_code(self):
        district = self._district()
        village = Village.objects.create(
            code="1", name="Oro-oro Ombo", district=district
        )

        resolved = ResponseBulkImportService._resolve_village("1", {})

        self.assertEqual(resolved, village)

    def test_resolve_village_unknown_raises(self):
        self._district()
        with self.assertRaises(BulkImportError):
            ResponseBulkImportService._resolve_village("999", {})

    def test_resolve_village_non_numeric_raises(self):
        with self.assertRaises(BulkImportError):
            ResponseBulkImportService._resolve_village("abc", {})

    def test_header_columns_recognize_z_indicator(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["ID Resp", "Desa", "X1.1", "Z1.1"])

        header_row, column_map = (
            ResponseBulkImportService._find_header_columns(ws)
        )

        self.assertEqual(header_row, 1)
        self.assertIn("x1.1", column_map)
        self.assertIn("z1.1", column_map)

    def test_build_questionnaire_map_includes_z(self):
        district = self._district()
        variable = Variable.objects.create(
            code="Z1", name="Resp 1", role="response", order=1
        )
        indicator = Indicator.objects.create(
            code="Z1.1", name="Ind Z1.1", variable=variable
        )
        questionnaire = Questionnaire.objects.create(
            indicator=indicator,
            question="Q",
            answer_type="likert",
            question_order=1,
        )

        column_map = {"id resp": 1, "desa": 2, "z1.1": 3}

        result = ResponseBulkImportService._build_questionnaire_map(
            column_map
        )

        self.assertIn("z1.1", result)
        self.assertEqual(result["z1.1"], questionnaire)
