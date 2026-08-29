import io
import math

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class AnalyticsPDFExport:

    @classmethod
    def export(cls, data):

        response = HttpResponse(
            content_type="application/pdf"
        )

        response["Content-Disposition"] = (
            'attachment; filename="analytics_report.pdf"'
        )

        doc = SimpleDocTemplate(
            response,
            pagesize=A4,
        )

        styles = getSampleStyleSheet()

        story = []

        story.append(
            Paragraph(
                "Laporan Analytics - VillageInsight DSS",
                styles["Title"],
            )
        )

        story.append(Spacer(1, 12))

        story += cls._section_summary(data, styles)

        story += cls._section_clustering(data, styles)

        story += cls._section_feature_importance(data, styles)

        story += cls._section_radar(data, styles)

        story += cls._section_topsis(data, styles)

        story += cls._section_conclusion(data, styles)

        doc.build(story)

        return response

    # =========================================================

    @staticmethod
    def _table_style():

        return TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#0d6efd"),
            ),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ])

    @classmethod
    def _section_summary(cls, data, styles):

        summary = data["summary"]

        story = [
            Paragraph("Ringkasan Survey", styles["Heading2"]),
        ]

        rows = [
            ["Keterangan", "Nilai"],
            ["Jumlah Desa", summary["total_village"]],
            ["Jumlah Responden", summary["total_respondent"]],
            ["Jumlah Response", summary["total_response"]],
            ["Jumlah Cluster", summary["n_clusters"]],
            [
                "Silhouette Score",
                (
                    round(summary["silhouette_score"], 4)
                    if summary["silhouette_score"] is not None
                    else "-"
                ),
            ],
        ]

        table = Table(rows, colWidths=[8 * cm, 8 * cm])

        table.setStyle(cls._table_style())

        story.append(table)

        story.append(Spacer(1, 16))

        return story

    @classmethod
    def _section_clustering(cls, data, styles):

        story = [
            Paragraph("Hasil Clustering Desa", styles["Heading2"]),
        ]

        rows = [["Rank", "Desa", "Cluster", "Total Score"]]

        for row in data["village_table"]:

            rows.append([

                row["rank"],

                row["village"].name,

                row["cluster"].name if row["cluster"] else "-",

                round(float(row["total_score"]), 2),

            ])

        table = Table(
            rows,
            colWidths=[2 * cm, 5 * cm, 5 * cm, 4 * cm],
            repeatRows=1,
        )

        table.setStyle(cls._table_style())

        story.append(table)

        story.append(Spacer(1, 16))

        return story

    @classmethod
    def _section_feature_importance(cls, data, styles):

        story = [
            Paragraph(
                "Indikator/Variabel Paling Dominan",
                styles["Heading2"],
            ),
        ]

        variables = data["variable_importance"]

        if not variables:

            story.append(
                Paragraph(
                    "Belum ada hasil feature importance.",
                    styles["Normal"],
                )
            )

            return story

        names = [item["name"] for item in variables]

        values = [item["percentage"] for item in variables]

        fig, ax = plt.subplots(figsize=(6, 3.2))

        ax.barh(names[::-1], values[::-1], color="#0d6efd")

        ax.set_xlabel("Kontribusi (%)")

        fig.tight_layout()

        buffer = io.BytesIO()

        fig.savefig(buffer, format="png", dpi=150)

        plt.close(fig)

        buffer.seek(0)

        story.append(
            Image(buffer, width=15 * cm, height=8 * cm)
        )

        story.append(Spacer(1, 16))

        return story

    @classmethod
    def _section_radar(cls, data, styles):

        village = data["representative_village"]

        story = [
            Paragraph(
                (
                    "Radar Chart Indikator Dominan Desa: "
                    f"{village.name if village else '-'}"
                ),
                styles["Heading2"],
            ),
        ]

        radar = data["radar_data"]

        if not radar:

            story.append(
                Paragraph(
                    "Belum ada data radar untuk desa ini.",
                    styles["Normal"],
                )
            )

            return story

        labels = [axis["code"] for axis in radar]

        values = [axis["score"] for axis in radar]

        values += values[:1]

        angles = [
            n / float(len(labels)) * 2 * math.pi
            for n in range(len(labels))
        ]

        angles += angles[:1]

        fig = plt.figure(figsize=(5, 5))

        ax = fig.add_subplot(111, polar=True)

        ax.plot(angles, values, color="#0d6efd", linewidth=2)

        ax.fill(angles, values, color="#0d6efd", alpha=0.25)

        ax.set_xticks(angles[:-1])

        ax.set_xticklabels(labels)

        ax.set_ylim(0, 5)

        buffer = io.BytesIO()

        fig.savefig(buffer, format="png", dpi=150)

        plt.close(fig)

        buffer.seek(0)

        story.append(
            Image(buffer, width=10 * cm, height=10 * cm)
        )

        story.append(Spacer(1, 16))

        return story

    @classmethod
    def _section_topsis(cls, data, styles):

        story = [
            Paragraph(
                "Ranking Prioritas (TOPSIS per Cluster)",
                styles["Heading2"],
            ),
        ]

        for group in data["cluster_ranking"]:

            cluster_name = (
                group["cluster"].name
                if group["cluster"]
                else "Belum Dikluster"
            )

            story.append(
                Paragraph(cluster_name, styles["Heading3"])
            )

            rows = [["Rank", "Desa", "Skor Preferensi"]]

            for item in group["ranking"]:

                rows.append([

                    item["rank"],

                    item["village"].name,

                    (
                        round(item["score"], 4)
                        if item["score"] is not None
                        else "-"
                    ),

                ])

            table = Table(
                rows,
                colWidths=[2 * cm, 8 * cm, 6 * cm],
            )

            table.setStyle(cls._table_style())

            story.append(table)

            story.append(Spacer(1, 12))

        return story

    @classmethod
    def _section_conclusion(cls, data, styles):

        return [

            Paragraph("Kesimpulan Otomatis", styles["Heading2"]),

            Paragraph(data["narrative"], styles["Normal"]),

        ]
