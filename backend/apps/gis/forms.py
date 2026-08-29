import json
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from common.forms import BootstrapModelForm

from apps.gis.models import (
    CLOSED_DAY_CHOICES,
    ParkingFee,
    RegionCharacteristic,
    RegionElevation,
    TicketBundle,
    TourismCategory,
    TouristDestination,
    Wahana,
)


class BootstrapCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """
    ``CheckboxSelectMultiple`` yang merender tiap opsi sebagai checkbox
    Bootstrap (``form-check form-check-inline`` + ``form-check-input``).
    """

    option_template_name = "gis/widgets/checkbox_option.html"

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        option["attrs"]["class"] = "form-check-input"
        return option


class ClosedDaysField(forms.MultipleChoiceField):
    """
    Checkbox multi-pilih untuk ``TouristDestination.closed_days``
    (list int 0=Senin ... 6=Minggu). Kosong = buka setiap hari.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "choices",
            [(str(i), name) for i, name in CLOSED_DAY_CHOICES],
        )
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", BootstrapCheckboxSelectMultiple)
        kwargs.setdefault("label", "Hari Tutup")
        kwargs.setdefault(
            "help_text",
            "Centang hari yang TUTUP. Kosongkan semua = buka setiap hari.",
        )
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        # value dari model: list int (mis. [5, 6]) atau None.
        if value is None:
            return []
        return [str(v) for v in value]

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return []
        return sorted(int(v) for v in value)


class RegionCharacteristicForm(BootstrapModelForm):
    class Meta:
        model = RegionCharacteristic
        fields = [
            "village",
            "characteristic_type",
            "characteristic_name",
            "value",
            "value_type",
            "description",
            "source",
        ]
        labels = {
            "village": "Desa/Kelurahan",
            "characteristic_type": "Tipe Karakteristik",
            "characteristic_name": "Nama Karakteristik",
            "value": "Nilai",
            "value_type": "Tipe Nilai",
            "description": "Deskripsi",
            "source": "Sumber",
        }


class RegionElevationForm(BootstrapModelForm):
    class Meta:
        model = RegionElevation
        fields = [
            "village",
            "min_elevation",
            "max_elevation",
            "mean_elevation",
            "median_elevation",
            "std_deviation",
            "source_dataset",
            "resolution",
        ]
        labels = {
            "village": "Desa/Kelurahan",
            "min_elevation": "Ketinggian Minimum (m)",
            "max_elevation": "Ketinggian Maksimum (m)",
            "mean_elevation": "Rata-rata (m)",
            "median_elevation": "Median (m)",
            "std_deviation": "Standar Deviasi (m)",
            "source_dataset": "Sumber Dataset",
            "resolution": "Resolusi",
        }


class TourismCategoryForm(BootstrapModelForm):
    class Meta:
        model = TourismCategory
        fields = [
            "name",
            "description",
            "is_active",
        ]
        labels = {
            "name": "Nama Kategori",
            "description": "Deskripsi",
            "is_active": "Aktif",
        }


class TouristDestinationValidationMixin:
    """
    Validasi & normalisasi bersama untuk form destinasi (dipakai form
    situs maupun form admin), supaya aturan harga/status/jam konsisten.
    """

    def clean_ticket_type(self):
        # "Gratis" menonaktifkan field ini (tidak dikirim), jadi kosongkan
        # ke "unknown" supaya tidak ada nilai kosong.
        value = self.cleaned_data.get("ticket_type")
        return value or "unknown"

    def clean_place_type(self):
        # Default "attraction" (destinasi wisata) bila field tidak dikirim.
        value = self.cleaned_data.get("place_type")
        return value or "attraction"

    def clean_ticket_price_weekday(self):
        value = self.cleaned_data.get("ticket_price_weekday")
        if value is not None and value < 0:
            raise ValidationError("Harga tidak boleh negatif.")
        return value

    def clean_ticket_price_weekend(self):
        value = self.cleaned_data.get("ticket_price_weekend")
        if value is not None and value < 0:
            raise ValidationError("Harga tidak boleh negatif.")
        return value

    def clean_parking_cost(self):
        value = self.cleaned_data.get("parking_cost")
        if value is not None and value < 0:
            raise ValidationError("Biaya parkir tidak boleh negatif.")
        return value

    def clean_category_prices(self):
        value = self.cleaned_data.get("category_prices") or []
        if not isinstance(value, list):
            raise ValidationError("Format harga kategori harus list JSON.")
        for item in value:
            if not isinstance(item, dict) or "price" not in item:
                raise ValidationError(
                    "Setiap kategori harus berbentuk "
                    '{"category": "...", "price": ...}.'
                )
            if item.get("price") is not None and item["price"] < 0:
                raise ValidationError("Harga kategori tidak boleh negatif.")
        return value

    def clean(self):
        cleaned = super().clean()

        is_active = cleaned.get("is_active")
        status_reason = (cleaned.get("status_reason") or "").strip()
        if is_active is False and not status_reason:
            self.add_error(
                "status_reason",
                "Alasan wajib diisi bila status Nonaktif.",
            )

        ticket_type = cleaned.get("ticket_type")
        weekday = cleaned.get("ticket_price_weekday")
        weekend = cleaned.get("ticket_price_weekend")
        category_prices = cleaned.get("category_prices") or []

        # Bila "Gratis" dicentang, harga tidak wajib diisi.
        if not cleaned.get("is_free"):
            if ticket_type == "fixed" and weekday is None and weekend is None:
                self.add_error(
                    "ticket_price_weekday",
                    "Isi harga tiket (weekday/weekend) untuk tipe "
                    "'Harga tetap'.",
                )
            if ticket_type == "category" and not category_prices:
                self.add_error(
                    "category_prices",
                    "Isi daftar harga kategori, atau pilih 'Harga tetap'.",
                )

        opening = cleaned.get("opening_time")
        closing = cleaned.get("closing_time")
        is_24h = cleaned.get("is_open_24_hours")
        if (
            not is_24h
            and opening is not None
            and closing is not None
            and closing <= opening
        ):
            self.add_error(
                "closing_time",
                "Jam tutup harus lebih besar dari jam buka (atau centang "
                "'Buka 24 jam').",
            )

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)

        # "Gratis" disimpan sebagai status, bukan angka 0 paksa.
        if obj.is_free:
            obj.ticket_type = "unknown"
            obj.ticket_price_weekday = None
            obj.ticket_price_weekend = None
            obj.category_prices = []
            obj.price_description = ""

        # "Bebas biaya parkir" -> kolom biaya parkir diabaikan.
        if obj.is_free_parking:
            obj.parking_cost = None

        if not obj.is_free and obj.ticket_type != "unknown":
            if obj.price_source_type == "manual" and not obj.price_source:
                obj.price_source = "Manual"
            obj.price_updated_at = timezone.now()

        if commit:
            obj.save()
            self.save_m2m()
        return obj


class TouristDestinationForm(
    TouristDestinationValidationMixin, BootstrapModelForm
):
    closed_days = ClosedDaysField()

    class Meta:
        model = TouristDestination
        fields = [
            "name",
            "village",
            "place_type",
            "tourism_type",
            "categories",
            "cuisine_types",
            "description",
            "latitude",
            "longitude",
            "google_maps_query",
            "price_min",
            "price_max",
            "ambiance",
            "photo",
            "estimated_duration_minutes",
            "opening_time",
            "closing_time",
            "is_open_24_hours",
            "closed_days",
            "is_free",
            "ticket_type",
            "ticket_price_weekday",
            "ticket_price_weekend",
            "is_free_parking",
            "parking_cost",
            "price_description",
            "category_prices",
            "price_source",
            "price_source_type",
            "price_source_url",
            "accessibility",
            "difficulty",
            "family_friendly",
            "elderly_friendly",
            "child_friendly",
            "indoor_outdoor",
            "is_active",
            "status_reason",
            "source",
        ]
        labels = {
            "name": "Nama Destinasi",
            "village": "Desa/Kelurahan",
            "place_type": "Jenis Tempat",
            "tourism_type": "Tipe Wisata",
            "categories": "Kategori Wisata",
            "cuisine_types": "Cita Rasa / Jenis Masakan",
            "description": "Deskripsi",
            "latitude": "Latitude",
            "longitude": "Longitude",
            "google_maps_query": "Google Maps Query",
            "price_min": "Harga Minimum (IDR)",
            "price_max": "Harga Maksimum (IDR)",
            "ambiance": "Suasana",
            "photo": "Foto (URL)",
            "estimated_duration_minutes": "Estimasi Durasi (menit)",
            "opening_time": "Jam Buka",
            "closing_time": "Jam Tutup",
            "is_open_24_hours": "Buka 24 Jam",
            "closed_days": "Hari Tutup",
            "is_free": "Gratis",
            "ticket_type": "Tipe Harga",
            "ticket_price_weekday": "Harga Tiket Weekday (IDR)",
            "ticket_price_weekend": "Harga Tiket Weekend (IDR)",
            "parking_cost": "Biaya Parkir (IDR)",
            "is_free_parking": "Bebas Biaya Parkir",
            "price_description": "Deskripsi Harga",
            "category_prices": "Harga per Kategori",
            "price_source": "Sumber Harga",
            "price_source_type": "Jenis Sumber Harga",
            "price_source_url": "URL Sumber Harga",
            "accessibility": "Aksesibilitas",
            "difficulty": "Tingkat Kesulitan",
            "family_friendly": "Ramah Keluarga",
            "elderly_friendly": "Ramah Lansia",
            "child_friendly": "Ramah Anak",
            "indoor_outdoor": "Dalam/Luar Ruangan",
            "is_active": "Status",
            "status_reason": "Alasan Nonaktif",
            "source": "Sumber",
        }
        widgets = {
            # Field JSON ini dirender sebagai hidden input; UI-nya memakai
            # dynamic repeater (JS) di template, bukan textarea JSON.
            "category_prices": forms.HiddenInput(),
            "price_description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["place_type"].required = False
        self.fields["is_active"].widget = forms.Select(
            choices=((True, "Aktif"), (False, "Nonaktif"))
        )
        # BootstrapModelForm menambah "form-control" & placeholder ke widget
        # checkbox multi-pilih, sehingga checkbox "Hari Tutup" tidak tampil.
        # Bersihkan agar dirender sebagai form-check.
        self.fields["closed_days"].widget.attrs["class"] = ""
        self.fields["closed_days"].widget.attrs.pop("placeholder", None)

        # Field JSON hidden untuk data wahana & bundle (diisi dynamic
        # repeater JS). Bukan model field — disinkronkan manual di save().
        self.fields["wahana_data"] = forms.CharField(
            widget=forms.HiddenInput(),
            required=False,
            initial=self._initial_wahana_json(),
        )
        self.fields["bundle_data"] = forms.CharField(
            widget=forms.HiddenInput(),
            required=False,
            initial=self._initial_bundle_json(),
        )
        self.fields["parking_data"] = forms.CharField(
            widget=forms.HiddenInput(),
            required=False,
            initial=self._initial_parking_json(),
        )

    # ---------------------------------------------------------
    # Serialisasi data relational -> JSON (untuk repeater JS)
    # ---------------------------------------------------------

    def _initial_wahana_json(self):
        if not self.instance.pk:
            return "[]"
        items = [
            {
                "id": w.id,
                "name": w.name,
                "pricing_type": w.pricing_type,
                "price": w.price_int,
                "bundle_ids": [b.id for b in w.bundles.all()],
            }
            for w in self.instance.wahanas.all().order_by("name")
        ]
        return json.dumps(items, ensure_ascii=False)

    def _initial_bundle_json(self):
        if not self.instance.pk:
            return "[]"
        items = [
            {
                "id": b.id,
                "name": b.name,
                "price": b.price_int,
                "includes_entry_ticket": b.includes_entry_ticket,
                "ride_names": [w.name for w in b.wahanas.all()],
            }
            for b in self.instance.bundles.all().order_by("name")
        ]
        return json.dumps(items, ensure_ascii=False)

    def _initial_parking_json(self):
        if not self.instance.pk:
            return "[]"
        items = [
            {
                "id": f.id,
                "vehicle_type": f.vehicle_type,
                "price": f.price_int,
            }
            for f in self.instance.parking_fees.all().order_by("vehicle_type")
        ]
        return json.dumps(items, ensure_ascii=False)

    def pricing_type_options_json(self):
        """Pilihan kategori harga untuk dropdown JS (satu sumber data)."""
        return json.dumps(
            [{"value": v, "label": l} for v, l in Wahana.PRICING_TYPE_CHOICES],
            ensure_ascii=False,
        )

    # ---------------------------------------------------------
    # Parsing & validasi data JSON dari repeater
    # ---------------------------------------------------------

    @staticmethod
    def _parse_json(value):
        if not value:
            return []
        try:
            data = json.loads(value)
        except (TypeError, ValueError):
            raise ValidationError("Format data tidak valid (bukan JSON).")
        if not isinstance(data, list):
            raise ValidationError("Format data harus berupa list.")
        return data

    @staticmethod
    def _to_decimal(value):
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(f"Harga tidak valid: {value}")

    def clean_wahana_data(self):
        value = self.cleaned_data.get("wahana_data")
        items = self._parse_json(value)

        valid_types = {v for v, _ in Wahana.PRICING_TYPE_CHOICES}
        seen_names = set()
        cleaned = []
        for item in items:
            if not isinstance(item, dict):
                raise ValidationError("Setiap wahana harus berbentuk objek.")
            name = str(item.get("name") or "").strip()
            if not name:
                continue  # baris kosong diabaikan
            key = name.lower()
            if key in seen_names:
                raise ValidationError(
                    f"Nama wahana duplikat: {name}. Gunakan nama unik."
                )
            seen_names.add(key)

            pricing_type = item.get("pricing_type") or Wahana.PRICE_UNKNOWN
            if pricing_type not in valid_types:
                pricing_type = Wahana.PRICE_UNKNOWN

            price = self._to_decimal(item.get("price"))

            if pricing_type == Wahana.INDEPENDENT_PRICE and price is None:
                raise ValidationError(
                    f"Wahana '{name}' berbayar wajib diisi harganya."
                )
            if pricing_type != Wahana.INDEPENDENT_PRICE:
                price = None
            if price is not None and price < 0:
                raise ValidationError(
                    f"Harga wahana '{name}' tidak boleh negatif."
                )

            # Wahana "Termasuk Paket/Tiket" membawa relasi ke bundle (by name).
            bundle_names = []
            if pricing_type == Wahana.INCLUDED_IN_PACKAGE:
                bundle_names = [
                    str(n).strip()
                    for n in (item.get("bundle_names") or [])
                    if str(n).strip()
                ]

            cleaned.append({
                "id": item.get("id"),
                "name": name,
                "pricing_type": pricing_type,
                "price": price,
                "bundle_names": bundle_names,
            })

        self._cleaned_wahanas = cleaned
        return value

    def clean_bundle_data(self):
        value = self.cleaned_data.get("bundle_data")
        items = self._parse_json(value)

        seen_names = set()
        cleaned = []
        for item in items:
            if not isinstance(item, dict):
                raise ValidationError("Setiap bundle harus berbentuk objek.")
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen_names:
                raise ValidationError(
                    f"Nama bundle duplikat: {name}. Gunakan nama unik."
                )
            seen_names.add(key)

            price = self._to_decimal(item.get("price"))
            if price is not None and price < 0:
                raise ValidationError(f"Harga bundle '{name}' tidak boleh negatif.")

            ride_names = [
                str(r).strip()
                for r in (item.get("ride_names") or [])
                if str(r).strip()
            ]
            cleaned.append({
                "id": item.get("id"),
                "name": name,
                "price": price,
                "includes_entry_ticket": bool(item.get("includes_entry_ticket")),
                "ride_names": ride_names,
            })

        self._cleaned_bundles = cleaned
        return value

    def clean_parking_data(self):
        value = self.cleaned_data.get("parking_data")
        items = self._parse_json(value)

        seen_types = set()
        cleaned = []
        for item in items:
            if not isinstance(item, dict):
                raise ValidationError("Setiap biaya parkir harus berbentuk objek.")
            vehicle_type = str(item.get("vehicle_type") or "").strip()
            if not vehicle_type:
                continue
            key = vehicle_type.lower()
            if key in seen_types:
                raise ValidationError(
                    f"Jenis kendaraan parkir duplikat: {vehicle_type}."
                )
            seen_types.add(key)

            price = self._to_decimal(item.get("price"))
            if price is None:
                raise ValidationError(
                    f"Biaya parkir '{vehicle_type}' wajib diisi."
                )
            if price < 0:
                raise ValidationError(
                    f"Biaya parkir '{vehicle_type}' tidak boleh negatif."
                )

            cleaned.append({
                "id": item.get("id"),
                "vehicle_type": vehicle_type,
                "price": price,
            })

        self._cleaned_parking = cleaned
        return value

    # ---------------------------------------------------------
    # Sync ke model relational
    # ---------------------------------------------------------

    def _sync_wahanas(self, destination):
        items = getattr(self, "_cleaned_wahanas", [])
        existing = {w.id: w for w in destination.wahanas.all()}
        existing_by_name = {
            w.name.lower(): w for w in existing.values()
        }

        kept_ids = set()
        name_to_wahana = {}
        self._package_links = {}
        for item in items:
            name = item["name"]
            wahana = None
            item_id = item.get("id")
            if item_id and item_id in existing:
                wahana = existing[item_id]
            elif name.lower() in existing_by_name:
                wahana = existing_by_name[name.lower()]

            if wahana is None:
                wahana = Wahana(destination=destination)

            wahana.name = name
            wahana.pricing_type = item["pricing_type"]
            wahana.price = item["price"]
            wahana.is_active = True
            wahana.save()

            if item["pricing_type"] == Wahana.INCLUDED_IN_PACKAGE:
                self._package_links[name.lower()] = item.get("bundle_names", [])

            kept_ids.add(wahana.id)
            name_to_wahana[name.lower()] = wahana

        # Hapus wahana yang dihapus dari form (relasi M2M ke bundle ikut
        # dibersihkan otomatis oleh Django — tidak ada orphan relationship).
        for w in destination.wahanas.exclude(id__in=kept_ids):
            w.delete()

        return name_to_wahana

    def _sync_bundles(self, destination, name_to_wahana):
        items = getattr(self, "_cleaned_bundles", [])
        existing = {b.id: b for b in destination.bundles.all()}
        existing_by_name = {b.name.lower(): b for b in existing.values()}

        kept_ids = set()
        name_to_bundle = {}
        for item in items:
            name = item["name"]
            bundle = None
            item_id = item.get("id")
            if item_id and item_id in existing:
                bundle = existing[item_id]
            elif name.lower() in existing_by_name:
                bundle = existing_by_name[name.lower()]

            if bundle is None:
                bundle = TicketBundle(destination=destination)

            bundle.name = name
            bundle.price = item["price"]
            bundle.includes_entry_ticket = item["includes_entry_ticket"]
            bundle.is_active = True
            bundle.save()

            # Set relasi ManyToMany: bundle <-> wahana (by name). Wahana yang
            # tidak ditemukan dilewati (nama sudah dibersihkan di form).
            selected = [
                name_to_wahana[n]
                for n in [r.lower() for r in item["ride_names"]]
                if n in name_to_wahana
            ]
            bundle.wahanas.set(selected)

            kept_ids.add(bundle.id)
            name_to_bundle[name.lower()] = bundle

        # Hapus bundle yang dihapus dari form. Wahana TIDAK ikut dihapus.
        for b in destination.bundles.exclude(id__in=kept_ids):
            b.delete()

        return name_to_bundle

    def _apply_wahana_package_links(self, name_to_wahana, name_to_bundle):
        """Terapkan relasi wahana->bundle untuk tipe INCLUDED_IN_PACKAGE."""
        for name_key, bundle_names in self._package_links.items():
            wahana = name_to_wahana.get(name_key)
            if wahana is None:
                continue
            selected = [
                name_to_bundle[n.lower()]
                for n in bundle_names
                if n.lower() in name_to_bundle
            ]
            wahana.bundles.set(selected)

    def _sync_parking_fees(self, destination):
        items = getattr(self, "_cleaned_parking", [])
        existing = {f.id: f for f in destination.parking_fees.all()}
        existing_by_type = {
            f.vehicle_type.lower(): f for f in existing.values()
        }

        kept_ids = set()
        for item in items:
            vehicle_type = item["vehicle_type"]
            fee = None
            item_id = item.get("id")
            if item_id and item_id in existing:
                fee = existing[item_id]
            elif vehicle_type.lower() in existing_by_type:
                fee = existing_by_type[vehicle_type.lower()]

            if fee is None:
                fee = ParkingFee(destination=destination)

            fee.vehicle_type = vehicle_type
            fee.price = item["price"]
            fee.is_active = True
            fee.save()
            kept_ids.add(fee.id)

        for f in destination.parking_fees.exclude(id__in=kept_ids):
            f.delete()

    def save(self, commit=True):
        obj = super().save(commit=commit)
        if commit:
            name_to_wahana = self._sync_wahanas(obj)
            name_to_bundle = self._sync_bundles(obj, name_to_wahana)
            self._apply_wahana_package_links(name_to_wahana, name_to_bundle)
            self._sync_parking_fees(obj)
        return obj


class ItineraryRequestForm(forms.Form):
    """
    Form permintaan itinerary/rundown (untuk halaman Generate Excel).
    Bukan model form — langsung dipetakan ke TripPlanningService.
    """

    duration_days = forms.IntegerField(
        label="Durasi (hari)",
        min_value=1,
        max_value=7,
        initial=1,
    )
    start_date = forms.DateField(
        label="Tanggal Mulai",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    traveler_count = forms.IntegerField(
        label="Jumlah Wisatawan",
        min_value=1,
        initial=1,
    )
    transportation = forms.ChoiceField(
        label="Transportasi",
        required=False,
        choices=[
            ("car", "Mobil"),
            ("motorcycle", "Motor"),
            ("walking", "Jalan kaki"),
            ("public", "Transportasi umum"),
        ],
    )
    vehicles = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        help_text="JSON daftar kendaraan (diisi repeater JS).",
    )
    budget = forms.IntegerField(
        label="Budget (Rp)",
        min_value=0,
        required=False,
    )
    budget_scope = forms.ChoiceField(
        label="Cakupan Budget",
        required=False,
        initial="total",
        choices=[("total", "Total"), ("per_person", "Per orang")],
    )
    preferences = forms.CharField(
        label="Preferensi",
        required=False,
        help_text="Pisahkan dengan koma, mis. alam, air terjun, keluarga.",
    )
    elderly = forms.BooleanField(label="Ada lansia", required=False)
    children = forms.BooleanField(label="Ada anak kecil", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"
