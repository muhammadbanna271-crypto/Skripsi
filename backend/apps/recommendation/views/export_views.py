from common.models.decorators import staff_required

from apps.recommendation.services import RecommendationService

from apps.recommendation.exports.excel_export import ExcelExport
from apps.recommendation.exports.pdf_export import PDFExport


@staff_required
def export_excel(request):

    ranking = RecommendationService.generate()

    return ExcelExport.export(ranking)


@staff_required
def export_pdf(request):

    ranking = RecommendationService.generate()

    return PDFExport.export(ranking)