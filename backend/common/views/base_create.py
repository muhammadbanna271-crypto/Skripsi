from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views.generic import CreateView


class BaseCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Base Create View

    Default: cuma staff/superuser yang boleh create. Kalau ada
    view yang butuh aturan beda (misal Survey/Respondent/Response
    yang punya toggle "allow_public_input"), tinggal override
    test_func() di view turunannya atau pakai SurveyAccessMixin
    (lihat common/mixins.py).
    """

    success_message = "Data created successfully."

    def test_func(self):
        return (
            self.request.user.is_staff
            or self.request.user.is_superuser
        )

    def handle_no_permission(self):

        if not self.request.user.is_authenticated:
            return super().handle_no_permission()

        messages.error(
            self.request,
            "Kamu tidak punya izin untuk melakukan aksi ini.",
        )

        return redirect(
            self.request.META.get("HTTP_REFERER", "dashboard:dashboard")
        )

    def form_valid(self, form):

        messages.success(
            self.request,
            self.success_message,
        )

        return super().form_valid(form)