"""
Django settings for VillageInsight DSS.

Version : 1.0.0
"""

from pathlib import Path
from dotenv import load_dotenv
import os
import dj_database_url
# --------------------------------------------------
# BASE DIRECTORY
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# --------------------------------------------------

load_dotenv(BASE_DIR.parent / ".env")

# --------------------------------------------------
# SECURITY
# --------------------------------------------------

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-change-this-secret-key"
)

# --------------------------------------------------
# CHATBOT (Claude API)
# --------------------------------------------------

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

CHATBOT_MODEL = os.getenv("CHATBOT_MODEL", "claude-sonnet-5")

CHATBOT_MAX_MESSAGES_PER_SESSION = int(
    os.getenv("CHATBOT_MAX_MESSAGES_PER_SESSION", "100")
)

# Lapis pengaman KEDUA di sisi aplikasi (lapis pertama & paling
# kuat tetap monthly spend limit di console.anthropic.com).
# Estimasi biaya per pesan pakai harga STANDAR Sonnet 5 yang
# berlaku mulai 1 Sept 2026 ($3/$15 per juta token), bukan harga
# promo yang sedang berjalan ($2/$10) -- supaya batasnya tetap
# valid dan tidak perlu diubah lagi bulan depan. Angkanya juga
# sengaja dilebihkan dari estimasi rata-rata sebagai margin aman.
CHATBOT_MONTHLY_BUDGET_USD = float(
    os.getenv("CHATBOT_MONTHLY_BUDGET_USD", "10")
)

CHATBOT_ESTIMATED_COST_PER_MESSAGE_USD = float(
    os.getenv("CHATBOT_ESTIMATED_COST_PER_MESSAGE_USD", "0.01")
)

# --------------------------------------------------
# DEEPSEEK (engine kedua, bebas akses tanpa password)
# --------------------------------------------------

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# --------------------------------------------------
# Password gate untuk engine Claude (biar pemakaiannya
# dibatasi manual, tidak sembarang orang bisa akses)
# --------------------------------------------------

CHATBOT_CLAUDE_PASSWORD = os.getenv("CHATBOT_CLAUDE_PASSWORD", "")

# FIXED: default DEBUG diubah ke "False". Kalau env var DEBUG lupa
# di-set di Railway (production), app tidak akan otomatis jalan
# dalam mode debug yang berbahaya (bisa expose info sensitif).
DEBUG = os.getenv("DEBUG", "False") == "True"

RAILWAY_HOST = os.getenv("RAILWAY_PUBLIC_DOMAIN")
ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost"
).split(",")

if RAILWAY_HOST:
    ALLOWED_HOSTS.append(RAILWAY_HOST)

# FIXED: tambahan wildcard ".up.railway.app". RAILWAY_PUBLIC_DOMAIN
# cuma nunjuk ke SATU domain (biasanya yang di-generate otomatis
# pertama kali), jadi kalau kamu tambah/rename domain lain lewat
# tombol "Generate Domain" / edit nama subdomain (misal trip1,
# tripdss, dst), domain baru itu TIDAK otomatis masuk ke
# RAILWAY_PUBLIC_DOMAIN dan bakal kena error 400 "DisallowedHost".
# Dengan wildcard ini, SEMUA subdomain *.up.railway.app yang kamu
# buat di project Railway ini otomatis diterima, tanpa perlu edit
# kode / env var manual tiap kali ganti nama domain.
ALLOWED_HOSTS.append(".up.railway.app")
# --------------------------------------------------
# APPLICATION DEFINITION
# --------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "django_filters",
    "widget_tweaks",
    "django_extensions",
]

LOCAL_APPS = [
    "apps.master",
]

INSTALLED_APPS = [

    # Django Apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Local Apps
    "common",
    "apps.master",
    "apps.survey",
    "apps.respondent",
    "apps.response",
    "apps.analytics",
    "apps.dashboard",
    "apps.recommendation.apps.RecommendationConfig",
    "apps.chatbot",
    "apps.gis.apps.GisConfig",

]

# --------------------------------------------------
# MIDDLEWARE
# --------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "common.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --------------------------------------------------
# ROOT URL
# --------------------------------------------------

ROOT_URLCONF = "config.urls"

# --------------------------------------------------
# TEMPLATE
# --------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --------------------------------------------------
# DATABASE
# --------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": os.getenv(
                "DB_ENGINE",
                "django.db.backends.sqlite3"
            ),
            "NAME": os.getenv(
                "DB_NAME",
                BASE_DIR / "db.sqlite3"
            ),
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", ""),
            "PORT": os.getenv("DB_PORT", ""),
        }
    }

# --------------------------------------------------
# PASSWORD VALIDATION
# --------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# --------------------------------------------------
# INTERNATIONALIZATION
# --------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Jakarta"

USE_I18N = True

USE_TZ = True

# --------------------------------------------------
# STATIC
# --------------------------------------------------

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

# --------------------------------------------------
# MEDIA
# --------------------------------------------------

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

# --------------------------------------------------
# DEFAULT PRIMARY KEY
# --------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------
# CRISPY FORMS
# --------------------------------------------------

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"

# --------------------------------------------------
# LOGIN
# --------------------------------------------------

LOGIN_URL = "login"

LOGIN_REDIRECT_URL = "dashboard:dashboard"

LOGOUT_REDIRECT_URL = "login"

# --------------------------------------------------
# SESSION
# --------------------------------------------------

# Sesi habis setelah 30 menit TIDAK AKTIF (rolling timeout), supaya
# user tidak "login selamanya". Ubah lewat env var SESSION_COOKIE_AGE.
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "1800"))

SESSION_SAVE_EVERY_REQUEST = True

# --------------------------------------------------
# LOGGING
# --------------------------------------------------

LOGGING = {

    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {

        "verbose": {

            "format": (
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            ),

        },

    },

    "handlers": {

        # PENTING: handler ini TIDAK pakai filter "require_debug_true",
        # jadi tetap nyetak ke stdout walau DEBUG=False (production).
        # Handler bawaan Django ("console") sengaja cuma aktif kalau
        # DEBUG=True, itu sebabnya traceback 500 selama ini gak pernah
        # muncul di Railway logs.
        "console_always": {

            "level": "ERROR",

            "class": "logging.StreamHandler",

            "formatter": "verbose",

        },

        # Untuk log timing/performa (INFO) — menemukan bottleneck
        # (query DB, LLM, itinerary, Excel, dst.) tanpa spam error.
        "console_info": {

            "level": "INFO",

            "class": "logging.StreamHandler",

            "formatter": "verbose",

        },

    },

    "loggers": {

        # Semua 500 (unhandled exception di view) lewat logger ini.
        "django.request": {

            "handlers": ["console_always"],

            "level": "ERROR",

            "propagate": False,

        },

        # Jaga-jaga buat error umum lain di luar request/response cycle.
        "django": {

            "handlers": ["console_always"],

            "level": "ERROR",

            "propagate": False,

        },

        # Timing/performa (LLM call, retrieval, itinerary, Excel).
        "timing": {

            "handlers": ["console_info"],

            "level": "INFO",

            "propagate": False,

        },

    },

}

STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

# FIXED: CSRF_TRUSTED_ORIGINS sekarang mencakup domain aktif dari
# RAILWAY_PUBLIC_DOMAIN (kalau ada) DITAMBAH wildcard
# "https://*.up.railway.app" -- supaya semua subdomain yang kamu
# buat/ganti di project Railway ini (trip1, tripdss, atau nama
# apapun nanti) otomatis dipercaya buat CSRF, tanpa perlu edit
# manual tiap kali ganti nama domain.
CSRF_TRUSTED_ORIGINS = [
    "https://*.up.railway.app",
]
if RAILWAY_HOST:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_HOST}")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --------------------------------------------------
# GIS & TRIP PLANNER
# --------------------------------------------------

# API key Google Maps (opsional). Dipakai untuk pengambilan harga dari
# sumber eksternal (Google Places). Tanpa key, provider otomatis dilewati
# dan sistem fallback ke input manual.
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Lokasi file GeoJSON batas desa (relatif terhadap BASE_DIR). File resmi
# harus dimasukkan sendiri oleh admin; sistem TIDAK membuat polygon palsu.
GIS_GEOJSON_PATH = os.getenv(
    "GIS_GEOJSON_PATH",
    "static/geo/batas_desa_kota_batu.geojson",
)

# GeoJSON zona ketinggian (region-level) — layer "Elevasi Wilayah".
GIS_ELEVATION_GEOJSON_PATH = os.getenv(
    "GIS_ELEVATION_GEOJSON_PATH",
    "static/geo/sebaran_ketinggian_kota_batu.geojson",
)

# GeoJSON karakteristik wilayah (region-level, per kecamatan).
GIS_CHARACTERISTIC_GEOJSON_PATH = os.getenv(
    "GIS_CHARACTERISTIC_GEOJSON_PATH",
    "static/geo/karakteristik_wilayah_kota_batu.geojson",
)

# GeoJSON suhu real-time per desa (hasil injeksi Open-Meteo).
GIS_TEMPERATURE_GEOJSON_PATH = os.getenv(
    "GIS_TEMPERATURE_GEOJSON_PATH",
    "static/geo/kota_batu_suhu_realtime_hourly.geojson",
)

# Palet warna cluster (categorical, urutan tetap & tervalidasi CVD-safe).
# Cluster akan diwarnai dari palet ini berdasarkan urutan code; kalau admin
# menetapkan warna custom di model Cluster (selain default), warna itu
# dipakai dan slot palet dilewati.
GIS_CLUSTER_PALETTE = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]

# Klasifikasi elevasi (sequential, satu hue biru muda -> tua).
# Batas kelas ini KONFIGURABLE -- kalibrasi ulang dengan data DEM resmi.
# "max": null berarti "sampai tak terbatas".
GIS_ELEVATION_CLASSES = [
    {"label": "Rendah", "min": 0, "max": 700, "color": "#86b6ef"},
    {"label": "Sedang", "min": 700, "max": 1000, "color": "#5598e7"},
    {"label": "Tinggi", "min": 1000, "max": 1400, "color": "#2a78d6"},
    {"label": "Sangat Tinggi", "min": 1400, "max": None, "color": "#1c5cab"},
]

# Bobot scoring trip planner (jumlah = 1.0). Transparan & mudah diubah.
GIS_TRIP_SCORING_WEIGHTS = {
    "preference_match": 0.30,
    "budget_compatibility": 0.15,
    "accessibility": 0.20,
    "family_elderly_suitability": 0.20,
    "opening_hours": 0.05,
    "distance": 0.10,
}

# Konfigurasi transportasi untuk estimasi biaya/jarak trip planner.
# "fuel_cost_per_km" adalah ASUMSI estimasi (bukan data riil) dan SELALU
# diberi label "estimasi" di output. Ubah/nonaktifkan (0) sesuai kebutuhan.
GIS_TRANSPORT_CONFIG = {
    "motorcycle": {"label": "Motor", "fuel_cost_per_km": 300, "avg_speed_kmh": 25},
    "car": {"label": "Mobil", "fuel_cost_per_km": 1500, "avg_speed_kmh": 30},
    "walking": {"label": "Jalan kaki", "fuel_cost_per_km": 0, "avg_speed_kmh": 4},
    "public": {"label": "Transportasi umum", "fuel_cost_per_km": 0, "avg_speed_kmh": 20},
}

# Asumsi jadwal itinerary (bisa diubah). Bukan data riil destinasi.
GIS_ITINERARY_DAY_START_MIN = 8 * 60        # 08:00
GIS_ITINERARY_DAY_END_MIN = 17 * 60         # 17:00
GIS_ITINERARY_LUNCH_START_MIN = 12 * 60     # 12:00
GIS_ITINERARY_LUNCH_END_MIN = 13 * 60       # 13:00
GIS_ITINERARY_DEFAULT_DURATION_MIN = 90     # durasi default bila tidak diketahui
GIS_ITINERARY_TRAVEL_BUFFER_MIN = 45        # jeda antar destinasi

# --------------------------------------------------
# END
# --------------------------------------------------