from django.http import HttpResponse

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
)


class PDFExport:

    @staticmethod
    def export(ranking):

        response = HttpResponse(
            content_type="application/pdf"
        )

        response["Content-Disposition"] = (
            'attachment; filename="recommendation.pdf"'
        )

        doc = SimpleDocTemplate(response)

        data = [
            [
                "Rank",
                "Village",
                "Preference",
            ]
        ]

        for i, item in enumerate(ranking, start=1):

            data.append([
                i,
                item["village"].name,
                round(item["score"], 4),
            ])

        table = Table(data)

        doc.build([table])

        return response