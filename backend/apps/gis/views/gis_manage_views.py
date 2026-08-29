"""
View CRUD untuk data GIS & Pariwisata (staff/superuser only).

Authorization mengikuti base class existing (BaseCreateView/UpdateView/
DeleteView -> UserPassesTestMixin, hanya staff/superuser). List memakai
BaseListView (semua user login boleh lihat, tapi tombol add/edit/delete
disembunyikan otomatis lewat context ``can_edit``).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from common.views import (
    BaseCreateView,
    BaseDeleteView,
    BaseListView,
    BaseUpdateView,
)

from apps.gis.forms import (
    RegionCharacteristicForm,
    RegionElevationForm,
    TourismCategoryForm,
    TouristDestinationForm,
)
from apps.gis.models import (
    RegionCharacteristic,
    RegionElevation,
    TourismCategory,
    TouristDestination,
)
from apps.gis.services.price_source import PriceSourceService


class StaffRequiredListView(BaseListView):
    """
    List view khusus staff/superuser. ``BaseListView`` sekarang sudah
    staff-only, jadi tidak perlu mixin tambahan di sini.
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
            "Kamu tidak punya izin untuk mengakses menu ini.",
        )
        return redirect("dashboard:dashboard")


# =========================================================
# KARAKTERISTIK WILAYAH
# =========================================================

class RegionCharacteristicListView(StaffRequiredListView):
    model = RegionCharacteristic
    template_name = "gis/manage/characteristic_list.html"
    context_object_name = "characteristics"
    ordering = ["characteristic_type", "characteristic_name"]
    search_fields = [
        "village__name",
        "characteristic_type",
        "characteristic_name",
        "value",
    ]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("village")
        )


class RegionCharacteristicCreateView(BaseCreateView):
    model = RegionCharacteristic
    form_class = RegionCharacteristicForm
    template_name = "gis/manage/form.html"
    success_url = reverse_lazy("gis:manage-characteristic-list")
    success_message = "Karakteristik wilayah berhasil ditambahkan."
    extra_context = {
        "form_title": "Tambah Karakteristik Wilayah",
        "submit_label": "Simpan",
        "cancel_url": reverse_lazy("gis:manage-characteristic-list"),
    }


class RegionCharacteristicUpdateView(BaseUpdateView):
    model = RegionCharacteristic
    form_class = RegionCharacteristicForm
    template_name = "gis/manage/form.html"
    success_url = reverse_lazy("gis:manage-characteristic-list")
    success_message = "Karakteristik wilayah berhasil diperbarui."
    extra_context = {
        "form_title": "Ubah Karakteristik Wilayah",
        "submit_label": "Simpan",
        "cancel_url": reverse_lazy("gis:manage-characteristic-list"),
    }


class RegionCharacteristicDeleteView(BaseDeleteView):
    model = RegionCharacteristic
    template_name = "gis/manage/delete.html"
    success_url = reverse_lazy("gis:manage-characteristic-list")
    success_message = "Karakteristik wilayah berhasil dihapus."
    extra_context = {
        "cancel_url": reverse_lazy("gis:manage-characteristic-list"),
    }


# =========================================================
# ELEVASI WILAYAH
# =========================================================

class RegionElevationListView(StaffRequiredListView):
    model = RegionElevation
    template_name = "gis/manage/elevation_list.html"
    context_object_name = "elevations"
    ordering = ["village__name"]
    search_fields = ["village__name", "source_dataset"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("village")
        )


class RegionElevationCreateView(BaseCreateView):
    model = RegionElevation
    form_class = RegionElevationForm
    template_name = "gis/manage/form.html"
    success_url = reverse_lazy("gis:manage-elevation-list")
    success_message = "Data elevasi berhasil ditambahkan."
    extra_context = {
        "form_title": "Tambah Elevasi Wilayah",
        "submit_label": "Simpan",
        "cancel_url": reverse_lazy("gis:manage-elevation-list"),
    }


class RegionElevationUpdateView(BaseUpdateView):
    model = RegionElevation
    form_class = RegionElevationForm
    template_name = "gis/manage/form.html"
    success_url = reverse_lazy("gis:manage-elevation-list")
    success_message = "Data elevasi berhasil diperbarui."
    extra_context = {
        "form_title": "Ubah Elevasi Wilayah",
        "submit_label": "Simpan",
        "cancel_url": reverse_lazy("gis:manage-elevation-list"),
    }


class RegionElevationDeleteView(BaseDeleteView):
    model = RegionElevation
    template_name = "gis/manage/delete.html"
    success_url = reverse_lazy("gis:manage-elevation-list")
    success_message = "Data elevasi berhasil dihapus."
    extra_context = {
        "cancel_url": reverse_lazy("gis:manage-elevation-list"),
    }


# =========================================================
# KATEGORI WISATA
# =========================================================

class TourismCategoryListView(StaffRequiredListView):
    model = TourismCategory
    template_name = "gis/manage/category_list.html"
    context_object_name = "categories"
    ordering = ["name"]
    search_fields = ["name", "description"]


class TourismCategoryCreateView(BaseCreateView):
    model = TourismCategory
    form_class = TourismCategoryForm
    template_name = "gis/manage/form.html"
    success_url = reverse_lazy("gis:manage-category-list")
    success_message = "Kategori wisata berhasil ditambahkan."
    extra_context = {
        "form_title": "Tambah Kategori Wisata",
        "submit_label": "Simpan",
        "cancel_url": reverse_lazy("gis:manage-category-list"),
    }


class TourismCategoryUpdateView(BaseUpdateView):
    model = TourismCategory
    form_class = TourismCategoryForm
    template_name = "gis/manage/form.html"
    success_url = reverse_lazy("gis:manage-category-list")
    success_message = "Kategori wisata berhasil diperbarui."
    extra_context = {
        "form_title": "Ubah Kategori Wisata",
        "submit_label": "Simpan",
        "cancel_url": reverse_lazy("gis:manage-category-list"),
    }


class TourismCategoryDeleteView(BaseDeleteView):
    model = TourismCategory
    template_name = "gis/manage/delete.html"
    success_url = reverse_lazy("gis:manage-category-list")
    success_message = "Kategori wisata berhasil dihapus."
    extra_context = {
        "cancel_url": reverse_lazy("gis:manage-category-list"),
    }


# =========================================================
# DESTINASI WISATA
# =========================================================

class TouristDestinationListView(StaffRequiredListView):
    model = TouristDestination
    template_name = "gis/manage/destination_list.html"
    context_object_name = "destinations"
    ordering = ["name"]
    search_fields = [
        "name",
        "village__name",
        "tourism_type",
    ]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("village", "district", "village__district")
            .prefetch_related("categories")
        )


class TouristDestinationCreateView(BaseCreateView):
    model = TouristDestination
    form_class = TouristDestinationForm
    template_name = "gis/manage/destination_form.html"
    success_url = reverse_lazy("gis:manage-destination-list")
    success_message = "Destinasi wisata berhasil ditambahkan."
    extra_context = {
        "form_title": "Tambah Destinasi Wisata",
        "submit_label": "Simpan",
        "cancel_url": reverse_lazy("gis:manage-destination-list"),
    }


class TouristDestinationUpdateView(BaseUpdateView):
    model = TouristDestination
    form_class = TouristDestinationForm
    template_name = "gis/manage/destination_form.html"
    success_url = reverse_lazy("gis:manage-destination-list")
    success_message = "Destinasi wisata berhasil diperbarui."
    extra_context = {
        "form_title": "Ubah Destinasi Wisata",
        "submit_label": "Simpan",
        "cancel_url": reverse_lazy("gis:manage-destination-list"),
    }

    def get_success_url(self):
        # Kembali ke halaman & filter yang sama (bukan selalu halaman 1).
        next_url = (
            self.request.POST.get("next")
            or self.request.GET.get("next")
        )
        return next_url or self.success_url


class TouristDestinationDeleteView(BaseDeleteView):
    model = TouristDestination
    template_name = "gis/manage/delete.html"
    success_url = reverse_lazy("gis:manage-destination-list")
    success_message = "Destinasi wisata berhasil dihapus."
    extra_context = {
        "cancel_url": reverse_lazy("gis:manage-destination-list"),
    }

    def get_success_url(self):
        next_url = (
            self.request.POST.get("next")
            or self.request.GET.get("next")
        )
        return next_url or self.success_url


@login_required
@require_POST
def update_destination_price(request, pk):
    """
    Trigger "Update Harga" dari sumber eksternal (staff/superuser only).
    Gagal/tidak tersedia -> harga terakhir dipertahankan.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(
            request,
            "Kamu tidak punya izin untuk melakukan aksi ini.",
        )
        return redirect("dashboard:dashboard")

    destination = get_object_or_404(TouristDestination, pk=pk)
    result = PriceSourceService.update_destination(destination)

    if result.get("status") == "updated":
        messages.success(
            request,
            f"Harga berhasil diperbarui (sumber: {result.get('source')}).",
        )
    else:
        messages.warning(
            request,
            result.get("message", "Harga belum tersedia."),
        )

    return redirect(request.POST.get("next") or "gis:manage-destination-list")
