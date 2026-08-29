from django import forms
from django.contrib import admin

from apps.gis.forms import ClosedDaysField, TouristDestinationValidationMixin
from apps.gis.models import (
    CuisineType,
    ParkingFee,
    RegionCharacteristic,
    RegionElevation,
    TicketBundle,
    TourismCategory,
    TouristDestination,
    Wahana,
)


@admin.register(RegionCharacteristic)
class RegionCharacteristicAdmin(admin.ModelAdmin):
    list_display = (
        "village",
        "characteristic_type",
        "characteristic_name",
        "value",
        "value_type",
        "source",
        "updated_at",
    )
    search_fields = (
        "village__name",
        "characteristic_type",
        "characteristic_name",
        "value",
    )
    list_filter = (
        "characteristic_type",
        "value_type",
        "village__district",
    )
    ordering = ("characteristic_type", "characteristic_name")


@admin.register(RegionElevation)
class RegionElevationAdmin(admin.ModelAdmin):
    list_display = (
        "village",
        "min_elevation",
        "max_elevation",
        "mean_elevation",
        "std_deviation",
        "source_dataset",
        "updated_at",
    )
    search_fields = ("village__name", "source_dataset")
    list_filter = ("village__district",)
    ordering = ("village__name",)


@admin.register(TourismCategory)
class TourismCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "updated_at")
    search_fields = ("name",)
    list_filter = ("is_active",)
    ordering = ("name",)


@admin.register(Wahana)
class WahanaAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "destination",
        "pricing_type",
        "price",
        "is_active",
        "updated_at",
    )
    search_fields = ("name", "destination__name")
    list_filter = ("pricing_type", "is_active", "destination__village__district")
    ordering = ("destination__name", "name")


@admin.register(TicketBundle)
class TicketBundleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "destination",
        "price",
        "includes_entry_ticket",
        "is_active",
        "updated_at",
    )
    search_fields = ("name", "destination__name")
    list_filter = (
        "includes_entry_ticket",
        "is_active",
        "destination__village__district",
    )
    filter_horizontal = ("wahanas",)
    ordering = ("destination__name", "name")


@admin.register(ParkingFee)
class ParkingFeeAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle_type",
        "destination",
        "price",
        "is_active",
        "updated_at",
    )
    search_fields = ("vehicle_type", "destination__name")
    list_filter = ("is_active", "destination__village__district")
    ordering = ("destination__name", "vehicle_type")


@admin.register(CuisineType)
class CuisineTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "is_active", "updated_at")
    search_fields = ("name",)
    list_filter = ("kind", "is_active")
    ordering = ("kind", "name")


class TouristDestinationAdminForm(
    TouristDestinationValidationMixin, forms.ModelForm
):
    """
    Form admin khusus: ``closed_days`` pakai checkbox (ClosedDaysField),
    JSONField lain (facilities, accessibility_details) tetap textarea.
    Timestamp ``status_updated_at``/``price_updated_at`` dikelola otomatis.
    """

    closed_days = ClosedDaysField()

    class Meta:
        model = TouristDestination
        exclude = ("status_updated_at", "price_updated_at")


@admin.register(TouristDestination)
class TouristDestinationAdmin(admin.ModelAdmin):
    form = TouristDestinationAdminForm
    list_display = (
        "name",
        "place_type",
        "village",
        "effective_district",
        "tourism_type",
        "closed_days_display",
        "is_free",
        "is_free_parking",
        "ticket_type",
        "ticket_price_weekday",
        "ticket_price_weekend",
        "price_source",
        "is_open_24_hours",
        "is_active",
        "updated_at",
    )
    search_fields = (
        "name",
        "village__name",
        "tourism_type",
        "description",
    )
    list_filter = (
        "is_active",
        "place_type",
        "is_free",
        "is_free_parking",
        "ticket_type",
        "price_source_type",
        "is_open_24_hours",
        "tourism_type",
        "village__district",
        "categories",
    )
    filter_horizontal = ("categories", "cuisine_types")
    ordering = ("name",)

    @admin.display(description="Hari Tutup")
    def closed_days_display(self, obj):
        return obj.closed_days_display
