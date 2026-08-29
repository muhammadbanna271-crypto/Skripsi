from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views.generic import UpdateView


class BaseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Base Update View -- default staff/superuser only.
    """

    success_message = "Data updated successfully."

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