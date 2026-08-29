from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import ListView


class BaseListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Hanya staff/superuser yang boleh lihat list.
    """

    paginate_by = 10

    search_fields = []

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

    def get_queryset(self):

        queryset = super().get_queryset()

        keyword = self.request.GET.get("q")

        if keyword and self.search_fields:

            query = Q()

            for field in self.search_fields:

                query |= Q(**{
                    f"{field}__icontains": keyword
                })

            queryset = queryset.filter(query)

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # Dikirim ke SEMUA template list -- dipakai buat
        # nampilin/nyembunyiin tombol Add/Edit/Delete.
        context["can_edit"] = (
            self.request.user.is_staff
            or self.request.user.is_superuser
        )

        return context
