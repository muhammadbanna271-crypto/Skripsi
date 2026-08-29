from django.contrib import messages
from django.shortcuts import redirect, render

from apps.response.services.bulk_import_service import (
    BulkImportError,
    ResponseBulkImportService,
)
from apps.survey.models import Survey


def import_response(request):

    # Hanya staff dan superuser yang boleh mengakses Import Excel
    if not request.user.is_authenticated:
        return redirect("login")

    if not (
        request.user.is_staff
        or request.user.is_superuser
    ):
        messages.error(
            request,
            "Anda tidak memiliki izin untuk mengimpor data Excel.",
        )

        # Tetap render halaman ini, tapi tanpa data survey/form
        # karena user tidak punya akses
        return render(
            request,
            "response/response/import.html",
            {
                "surveys": [],
                "has_access": False,
            },
        )

    surveys = Survey.objects.all().order_by("-start_date")

    if request.method == "POST":

        survey_id = request.POST.get("survey_id")

        excel_file = request.FILES.get("excel_file")

        if not survey_id or not excel_file:

            messages.error(
                request,
                "Pilih survey dan file Excel terlebih dahulu.",
            )

            return redirect("response:response-import")

        survey = Survey.objects.filter(pk=survey_id).first()

        if survey is None:

            messages.error(
                request,
                "Survey tidak ditemukan.",
            )

            return redirect("response:response-import")

        try:

            result = ResponseBulkImportService.import_excel(
                excel_file,
                survey,
            )

        except BulkImportError as error:

            messages.error(
                request,
                str(error),
            )

            return redirect("response:response-import")

        except Exception as error:

            messages.error(
                request,
                f"Gagal memproses file: {error}",
            )

            return redirect("response:response-import")

        messages.success(
            request,
            (
                f"Import selesai. Respondent baru: "
                f"{result['created_respondent']}, "
                f"Respondent diperbarui: "
                f"{result['updated_respondent']}, "
                f"Jawaban tersimpan: {result['created_response']}."
            ),
        )

        if result["skipped_rows"]:

            messages.warning(
                request,
                (
                    f"{len(result['skipped_rows'])} baris dilewati. "
                    "Contoh: "
                    + "; ".join(result["skipped_rows"][:5])
                ),
            )

        return redirect(
            "response:response-import"
        )

    return render(
        request,
        "response/response/import.html",
        {
            "surveys": surveys,
            "has_access": True,
        },
    )