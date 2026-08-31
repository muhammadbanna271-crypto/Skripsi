import urllib.parse

from django.db import models
from django.utils import timezone

from common.models import BaseModel
from apps.master.models import District, Village


# Indeks hari mengikuti ``date.weekday()``: 0=Senin ... 6=Minggu.
DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
CLOSED_DAY_CHOICES = [(i, name) for i, name in enumerate(DAY_NAMES)]

# Tipe harga tiket. "unknown" = belum diketahui (BUKAN gratis). Status gratis
# disimpan terpisah di field ``is_free`` (checkbox) supaya tidak campur dengan
# "belum diketahui".
TICKET_TYPE_CHOICES = [
    ("unknown", "Belum diketahui"),
    ("fixed", "Harga tetap"),
    ("category", "Per kategori"),
]

# Kategori asal data harga, untuk membedakan input manual vs sumber eksternal.
PRICE_SOURCE_TYPE_CHOICES = [
    ("manual", "Manual"),
    ("scraping", "Scraping/API"),
    ("other", "Lainnya"),
]

# Jenis tempat: destinasi wisata (dengan HTM/wahana) vs restaurant/tempat makan
# (dengan range harga makanan, BUKAN tiket masuk).
PLACE_TYPE_CHOICES = [
    ("attraction", "Destinasi Wisata"),
    ("restaurant", "Restaurant / Tempat Makan"),
]


def format_idr(value):
    """Format angka jadi Rupiah Indonesia (Rp15.000). None -> None."""
    if value is None:
        return None
    try:
        return f"Rp{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return None


class TouristDestination(BaseModel):
    """
    Database destinasi wisata untuk mendukung PRUDENCE sebagai trip
    planner. Semua field harga/jam/aksesibilitas nullable & bertipe
    "belum diketahui" bila datanya belum ada — TIDAK mengarang nilai.
    """

    DIFFICULTY_CHOICES = [
        ("easy", "Mudah"),
        ("moderate", "Sedang"),
        ("hard", "Sulit"),
    ]

    INDOOR_OUTDOOR_CHOICES = [
        ("indoor", "Dalam Ruangan"),
        ("outdoor", "Luar Ruangan"),
        ("both", "Dalam & Luar Ruangan"),
    ]

    name = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name="Name",
    )

    village = models.ForeignKey(
        Village,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="destinations",
        verbose_name="Village",
    )

    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="destinations",
        verbose_name="District",
        help_text="Opsional; biasanya mengikuti kecamatan desa.",
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="Latitude",
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name="Longitude",
    )

    google_maps_query = models.CharField(
        max_length=300,
        blank=True,
        default="",
        verbose_name="Google Maps Query",
        help_text=(
            "Query pencarian Google Maps manual, mis. 'Batu Love Garden "
            "BALOGA, Kota Batu'. Bila kosong, sistem memakai nama + desa + "
            "Kota Batu."
        ),
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
    )

    tourism_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Tourism Type",
        help_text="Tipe utama (mis. alam, air terjun, budaya).",
    )

    place_type = models.CharField(
        max_length=20,
        choices=PLACE_TYPE_CHOICES,
        default="attraction",
        db_index=True,
        verbose_name="Jenis Tempat",
        help_text=(
            "Restaurant/tempat makan diperlakukan terpisah dari destinasi "
            "wisata (tidak punya HTM, memakai range harga makanan)."
        ),
    )

    categories = models.ManyToManyField(
        "gis.TourismCategory",
        related_name="destinations",
        blank=True,
        verbose_name="Categories",
    )

    cuisine_types = models.ManyToManyField(
        "gis.CuisineType",
        related_name="destinations",
        blank=True,
        verbose_name="Cita Rasa / Jenis Masakan",
    )

    price_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Harga Minimum (IDR)",
        help_text="Batas bawah range harga makanan (khusus restaurant).",
    )

    price_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Harga Maksimum (IDR)",
        help_text="Batas atas range harga makanan (khusus restaurant).",
    )

    ambiance = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Suasana",
        help_text="Mis. kasual, keluarga, formal, romantis.",
    )

    photo = models.URLField(
        blank=True,
        default="",
        verbose_name="Foto (URL)",
    )

    estimated_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Estimated Duration (minutes)",
    )

    opening_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Opening Time",
    )

    closing_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Closing Time",
    )

    is_open_24_hours = models.BooleanField(
        default=False,
        verbose_name="Open 24 Hours",
        help_text=(
            "Centang bila destinasi buka 24 jam. UI/chatbot akan "
            "menampilkan 'Buka 24 jam', bukan 00:00–23:59."
        ),
    )

    closed_days = models.JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name="Hari Tutup",
        help_text=(
            "List hari tutup (0=Senin … 6=Minggu). Kosong = buka setiap "
            "hari, null = belum diketahui."
        ),
    )

    is_free = models.BooleanField(
        default=False,
        verbose_name="Gratis",
        help_text=(
            "Centang bila destinasi GRATIS (tanpa tiket). Kolom harga "
            "akan diabaikan."
        ),
    )

    ticket_type = models.CharField(
        max_length=20,
        choices=TICKET_TYPE_CHOICES,
        default="unknown",
        blank=True,
        verbose_name="Ticket Type",
        help_text=(
            "'Harga tetap' untuk angka tunggal, 'Per kategori' bila ada "
            "beberapa harga, 'Belum diketahui' bila belum ada data."
        ),
    )

    ticket_price_weekday = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Ticket Price Weekday (IDR)",
        help_text="Harga tiket hari Senin–Jumat.",
    )

    ticket_price_weekend = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Ticket Price Weekend (IDR)",
        help_text="Harga tiket hari Sabtu–Minggu.",
    )

    parking_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Parking Cost (IDR)",
    )

    is_free_parking = models.BooleanField(
        default=False,
        verbose_name="Bebas Biaya Parkir",
        help_text=(
            "Centang bila parkir GRATIS. Kolom biaya parkir akan diabaikan."
        ),
    )

    price_description = models.TextField(
        blank=True,
        default="",
        verbose_name="Price Description",
        help_text=(
            "Deskripsi harga untuk ditampilkan, mis. 'Dewasa Rp20.000, "
            "Anak-anak Rp10.000'."
        ),
    )

    category_prices = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Category Prices",
        help_text=(
            "Harga per kategori (list of dict), contoh: "
            '[{"category": "Dewasa", "price": 20000}, '
            '{"category": "Anak-anak", "price": 10000}].'
        ),
    )

    price_source = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Price Source",
        help_text="Nama sumber harga, mis. 'Manual', 'Traveloka', 'Website Resmi'.",
    )

    price_source_type = models.CharField(
        max_length=20,
        choices=PRICE_SOURCE_TYPE_CHOICES,
        default="manual",
        blank=True,
        verbose_name="Price Source Type",
    )

    price_source_url = models.URLField(
        blank=True,
        default="",
        verbose_name="Price Source URL",
        help_text="URL sumber harga (jika ada).",
    )

    price_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Price Updated At",
    )

    accessibility = models.TextField(
        blank=True,
        default="",
        verbose_name="Accessibility",
        help_text="Deskripsi aksesibilitas umum (teks bebas).",
    )

    accessibility_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Accessibility Details",
        help_text=(
            "Detail terstruktur (kendaraan, akses mobil/motor, jalan "
            "sempit, medan, tangga, fasilitas lansia, toilet, dll.)."
        ),
    )

    elevation_meters = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Elevation (m)",
        help_text="Ketinggian (mdpl) hasil ekstraksi DEM.",
    )

    elevation_source = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Elevation Source",
        help_text="Sumber DEM, mis. 'DEMNAS', 'ALOS PALSAR'.",
    )

    temperature_c = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Temperature (°C)",
    )

    temperature_source = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Temperature Source",
        help_text="Sumber data suhu, mis. 'BMKG', 'WorldClim'.",
    )

    temperature_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Temperature Date",
        help_text="Tanggal/periode data suhu.",
    )

    difficulty = models.CharField(
        max_length=30,
        choices=DIFFICULTY_CHOICES,
        blank=True,
        default="",
        verbose_name="Difficulty",
    )

    family_friendly = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Family Friendly",
    )

    elderly_friendly = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Elderly Friendly",
    )

    child_friendly = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Child Friendly",
    )

    indoor_outdoor = models.CharField(
        max_length=20,
        choices=INDOOR_OUTDOOR_CHOICES,
        blank=True,
        default="",
        verbose_name="Indoor / Outdoor",
    )

    facilities = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Facilities",
        help_text="List fasilitas, mis. ['toilet', 'parkir', 'warung'].",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
    )

    status_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Status Reason",
        help_text=(
            "Alasan destinasi nonaktif (mis. sedang renovasi, tutup "
            "sementara). Wajib diisi bila status Nonaktif."
        ),
    )

    status_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Status Updated At",
    )

    source = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Source",
    )

    class Meta:
        db_table = "gis_tourist_destination"
        verbose_name = "Tourist Destination"
        verbose_name_plural = "Tourist Destinations"
        ordering = ["name"]

    def __str__(self):
        return self.name

    # ---------------------------------------------------------
    # Status active/inactive
    # ---------------------------------------------------------

    @property
    def status(self):
        """Nilai status kanonik (data/API): 'active' atau 'inactive'."""
        return "active" if self.is_active else "inactive"

    @property
    def status_label(self):
        """Label manusia (Bahasa Indonesia) sesuai UI yang ada."""
        return "Aktif" if self.is_active else "Nonaktif"

    def save(self, *args, **kwargs):
        """
        Catat ``status_updated_at`` setiap kali status active/inactive
        berubah (atau saat record baru dibuat).
        """
        if self.pk is not None:
            try:
                previous = TouristDestination.objects.get(pk=self.pk)
                changed = previous.is_active != self.is_active
            except TouristDestination.DoesNotExist:
                changed = True
        else:
            changed = True
        if changed:
            self.status_updated_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def effective_district(self):
        """Kecamatan efektif: pakai field district, fallback ke desa."""
        if self.district_id:
            return self.district
        if self.village_id:
            return self.village.district
        return None

    @property
    def ticket_price_weekday_int(self):
        return (
            int(self.ticket_price_weekday)
            if self.ticket_price_weekday is not None
            else None
        )

    @property
    def ticket_price_weekend_int(self):
        return (
            int(self.ticket_price_weekend)
            if self.ticket_price_weekend is not None
            else None
        )

    @property
    def parking_cost_int(self):
        if self.is_free_parking:
            return 0
        return int(self.parking_cost) if self.parking_cost is not None else None

    def parking_fee_for(self, vehicle_type):
        """
        Harga parkir untuk satu jenis kendaraan (case-insensitive).
        Fallback ke harga tunggal legacy ``parking_cost`` bila jenis
        kendaraan tidak punya tarif khusus.
        """
        fee = (
            self.parking_fees
            .filter(
                is_active=True,
                vehicle_type__iexact=str(vehicle_type or "").strip(),
            )
            .first()
        )
        if fee is not None:
            return int(fee.price)
        return self.parking_cost_int

    @property
    def min_category_price(self):
        """Harga kategori terkecil (estimasi konservatif), atau None."""
        prices = [
            item.get("price")
            for item in (self.category_prices or [])
            if isinstance(item, dict) and item.get("price") is not None
        ]
        if not prices:
            return None
        try:
            return min(int(p) for p in prices)
        except (TypeError, ValueError):
            return None

    def ticket_price_for(self, date=None):
        """
        Harga tiket (angka tunggal) untuk tanggal tertentu.

        - is_free      -> 0 (gratis, BUKAN 'belum diketahui')
        - "category"  -> harga kategori terkecil (estimasi konservatif)
        - "fixed"/legacy -> harga weekday/weekend sesuai tanggal; None
          bila sama sekali belum tersedia.
        """
        if self.is_free:
            return 0
        if self.ticket_type == "category":
            return self.min_category_price

        if date is not None:
            return (
                self.ticket_price_weekend_int
                if date.weekday() >= 5
                else self.ticket_price_weekday_int
            )

        if self.ticket_price_weekday_int is not None:
            return self.ticket_price_weekday_int
        if self.ticket_price_weekend_int is not None:
            return self.ticket_price_weekend_int
        return None

    # ---------------------------------------------------------
    # Label tampilan (harga & jam operasional)
    # ---------------------------------------------------------

    @property
    def price_range_display(self):
        """Range harga makanan (restaurant), mis. 'Rp20.000–Rp50.000'."""
        if self.price_min is None and self.price_max is None:
            return None
        if self.price_min is not None and self.price_max is not None:
            return f"{format_idr(self.price_min)}–{format_idr(self.price_max)}"
        if self.price_max is not None:
            return f"≤ {format_idr(self.price_max)}"
        return f"≥ {format_idr(self.price_min)}"

    @property
    def price_display(self):
        """Ringkasan harga siap tampil (UI/chatbot/Excel)."""
        if self.place_type == "restaurant":
            return self.price_range_display or "Belum tersedia"
        if self.is_free:
            return "Gratis"
        if self.ticket_type == "category":
            if self.price_description:
                return self.price_description
            if self.category_prices:
                parts = [
                    f"{item.get('category', '?')} {format_idr(item.get('price'))}"
                    for item in self.category_prices
                    if isinstance(item, dict) and item.get("price") is not None
                ]
                if parts:
                    return ", ".join(parts)
            return "Per kategori"
        price = self.ticket_price_for()
        if price is None:
            return "Belum tersedia"
        return format_idr(price)

    @property
    def price_type_display(self):
        """Label "Tipe Harga" konsisten di seluruh UI.

        Prioritas: Gratis (``is_free``) > Berbayar (fixed/category) >
        "Belum diketahui". Restaurant ditandai "Range Harga" karena tidak
        punya tiket masuk. Dipakai dashboard/list supaya "Gratis" tidak
        pernah tampil sebagai "Belum diketahui".
        """
        if self.place_type == "restaurant":
            return "Range Harga"
        if self.is_free:
            return "Gratis"
        if self.ticket_type == "fixed":
            return "Berbayar"
        if self.ticket_type == "category":
            return "Per Kategori"
        return "Belum diketahui"

    @property
    def weekday_price_display(self):
        """Tampilan harga weekday untuk tabel/list (konsisten di seluruh UI).

        Prioritas: Restaurant ("Tidak ada HTM") > Gratis > harga > belum.
        """
        if self.place_type == "restaurant":
            return "Tidak ada HTM"
        if self.is_free:
            return "Gratis"
        if self.ticket_price_weekday_int is not None:
            return format_idr(self.ticket_price_weekday_int)
        return "Belum tersedia"

    @property
    def weekend_price_display(self):
        """Tampilan harga weekend untuk tabel/list (konsisten di seluruh UI)."""
        if self.place_type == "restaurant":
            return "Tidak ada HTM"
        if self.is_free:
            return "Gratis"
        if self.ticket_price_weekend_int is not None:
            return format_idr(self.ticket_price_weekend_int)
        return "Belum tersedia"

    @property
    def group_label(self):
        """Label grup untuk daftar destinasi (dinamis dari data, bukan hardcode).

        Restaurant dikelompokkan sebagai "Tempat Makan"; destinasi wisata
        dikelompokkan berdasarkan ``tourism_type`` (uppercase). Tipe baru
        otomatis menjadi grup baru.
        """
        if self.place_type == "restaurant":
            return "TEMPAT MAKAN"
        return (self.tourism_type or "Lainnya").strip().upper()

    @property
    def parking_display(self):
        """Ringkasan biaya parkir siap tampil (UI/chatbot/Excel)."""
        if self.is_free_parking:
            return "Gratis"
        if self.parking_cost is not None:
            return format_idr(self.parking_cost)
        return "Belum tersedia"

    @property
    def active_wahanas(self):
        """Wahana aktif, urut nama (cache-aware: pakai .all() prefetch)."""
        return sorted(
            (w for w in self.wahanas.all() if w.is_active),
            key=lambda w: (w.name or "").lower(),
        )

    @property
    def active_bundles(self):
        """Bundle aktif, urut nama (cache-aware)."""
        return sorted(
            (b for b in self.bundles.all() if b.is_active),
            key=lambda b: (b.name or "").lower(),
        )

    @property
    def active_parking_fees(self):
        """Biaya parkir aktif, urut jenis kendaraan (cache-aware)."""
        return sorted(
            (f for f in self.parking_fees.all() if f.is_active),
            key=lambda f: (f.vehicle_type or "").lower(),
        )

    @property
    def parking_fees_display(self):
        """Ringkasan biaya parkir per kendaraan, atau None bila kosong."""
        parts = [
            f"{fee.vehicle_type} {fee.price_display}"
            for fee in self.active_parking_fees
        ]
        return ", ".join(parts) if parts else None

    @property
    def ride_prices_display(self):
        """Ringkasan harga wahana (relational), atau None bila tidak ada."""
        parts = [
            f"{w.name} {w.price_display}"
            for w in self.active_wahanas
        ]
        return ", ".join(parts) if parts else None

    @property
    def bundle_prices_display(self):
        """Ringkasan paket bundle (relational), atau None bila tidak ada."""
        parts = []
        for b in self.active_bundles:
            components = []
            if b.includes_entry_ticket:
                components.append("HTM")
            for w in b.wahanas.all():
                components.append(w.name)
            label = f"{b.name} ({' + '.join(components)})" if components else b.name
            parts.append(f"{label} {b.price_display}")
        return "; ".join(parts) if parts else None

    @property
    def operating_hours_display(self):
        """Label jam operasional: 'Buka 24 jam', 'HH:MM–HH:MM', atau 'Belum tersedia'."""
        if self.is_open_24_hours:
            return "Buka 24 jam"
        if self.opening_time and self.closing_time:
            return (
                f"{self.opening_time.strftime('%H:%M')}–"
                f"{self.closing_time.strftime('%H:%M')}"
            )
        return "Belum tersedia"

    # ---------------------------------------------------------
    # Google Maps
    # ---------------------------------------------------------

    @property
    def effective_google_maps_query(self):
        """
        Query pencarian Google Maps yang dipakai membangun link.
        Prioritas: ``google_maps_query`` manual (nama + alamat) -> nama +
        desa + "Kota Batu" -> (koordinat tidak lagi diprioritaskan).
        """
        if self.google_maps_query:
            return self.google_maps_query
        parts = [self.name]
        if self.village_id and self.village is not None:
            parts.append(self.village.name)
        parts.append("Kota Batu")
        return " ".join(part for part in parts if part)

    def google_maps_url(self):
        """
        Bangun Google Maps search URL.

        Prioritas:
          1. ``google_maps_query`` manual (staff sengaja isi nama+alamat
             yang lebih spesifik),
          2. koordinat (``lat,lng``) — supaya link menunjuk LOKASI YANG SAMA
             dengan marker peta, bukan pencarian nama yang bisa ambigu
             (mis. "Bubur Ayam Jakarta" punya banyak cabang),
          3. fallback nama + desa + Kota Batu.
        """
        if self.google_maps_query:
            query = self.google_maps_query
        elif self.latitude is not None and self.longitude is not None:
            query = f"{self.latitude},{self.longitude}"
        else:
            query = self.effective_google_maps_query
        return (
            "https://www.google.com/maps/search/?api=1&query="
            + urllib.parse.quote(query)
        )

    # ---------------------------------------------------------
    # Jadwal tutup (closed_days)
    # ---------------------------------------------------------

    @property
    def is_open_every_day(self):
        """True hanya bila diketahui buka setiap hari (closed_days == [])."""
        return self.closed_days == []

    @property
    def closed_days_display(self):
        """Label manusia: 'Buka setiap hari' / 'Tutup: Sabtu, Minggu' / None."""
        if self.closed_days is None:
            return "Belum diketahui"
        if not self.closed_days:
            return "Buka setiap hari"
        names = [
            DAY_NAMES[d]
            for d in sorted(self.closed_days)
            if isinstance(d, int) and 0 <= d <= 6
        ]
        return "Tutup: " + ", ".join(names)

    def is_open_on_weekday(self, weekday):
        """
        Apakah buka pada ``weekday`` (0=Senin ... 6=Minggu)?
        Return True/False/None (None = belum diketahui).
        """
        if self.closed_days is None:
            return None
        if not self.closed_days:
            return True
        return weekday not in self.closed_days

    def is_open_on(self, day):
        """
        Apakah buka pada ``day`` (datetime.date)? Return True/False/None.
        """
        return self.is_open_on_weekday(day.weekday())

    def is_open_at_time(self, total_minutes):
        """
        Apakah buka pada jam tertentu (menit sejak 00:00)?

        Return True/False/None:
          - True  : dipastikan buka pada menit tersebut,
          - False : dipastikan TUTUP,
          - None  : jam buka belum diketahui (tidak bisa dipastikan).

        Dipakai chatbot & itinerary engine (satu sumber logika yang sama).
        """
        if self.is_open_24_hours:
            return True
        if self.opening_time is None or self.closing_time is None:
            return None
        opening = self.opening_time.hour * 60 + self.opening_time.minute
        closing = self.closing_time.hour * 60 + self.closing_time.minute
        if closing <= opening:
            # Buka melewati tengah malam (mis. 22:00–02:00).
            return total_minutes >= opening or total_minutes < closing
        return opening <= total_minutes < closing
