from django.contrib import messages
from django.shortcuts import redirect, render

from apps.dataquality.pipeline import ValidatedImportService
from apps.dataquality.wording import result_messages
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

            execution = ValidatedImportService.run(
                excel_file,
                survey,
            )

        except Exception as error:

            messages.error(
                request,
                "File tidak dapat diproses karena terjadi kesalahan di "
                "sistem. Mohon coba lagi, atau hubungi pengelola sistem "
                f"bila masalah berulang. (Keterangan teknis: {error})",
            )

            return redirect("response:response-import")

        levels = {
            "success": messages.success,
            "warning": messages.warning,
            "error": messages.error,
        }

        for level, text in result_messages(execution):

            levels[level](request, text)

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