from openpyxl import Workbook
from django.http import HttpResponse


class ExcelExport:

    @staticmethod
    def export(ranking):

        wb = Workbook()

        ws = wb.active

        ws.title = "Recommendation"

        ws.append([
            "Rank",
            "Village",
            "Preference",
        ])

        for i, item in enumerate(ranking, start=1):

            ws.append([
                i,
                item["village"].name,
                item["score"],
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        response["Content-Disposition"] = (
            'attachment; filename="recommendation.xlsx"'
        )

        wb.save(response)

        return response