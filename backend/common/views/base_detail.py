from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views.generic import DetailView


class BaseDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Hanya staff/superuser yang boleh lihat detail.
    """

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
            "Kamu tidak punya izin untuk mengakses halaman ini.",
        )

        return redirect(
            self.request.META.get("HTTP_REFERER", "dashboard:dashboard")
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["can_edit"] = (
            self.request.user.is_staff
            or self.request.user.is_superuser
        )

        return context
