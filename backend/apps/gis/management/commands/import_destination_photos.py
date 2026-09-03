"""
Ambil foto destinasi wisata dari Wikimedia Commons (gratis, bebas lisensi).

Untuk tiap destinasi aktif:
- cari di Wikimedia Commons (namespace File = gambar saja),
- pilih kandidat terbaik yang judulnya cocok dengan nama destinasi,
- isi field `photo` dengan URL gambar (thumbnail 800px).

Heuristik "cocok": semua token penting nama destinasi (panjang > 2, bukan
stopword) harus muncul di judul file. Nama yang tidak yakin cocok akan
dilewati (tidak diisi) supaya tidak memasang foto yang salah.

Mode aman (default): dry-run — hanya menampilkan hasil, TIDAK menulis DB.
Tambahkan `--apply` untuk benar-benar menyimpan.

Jalankan:
    python manage.py import_destination_photos            # lihat dulu
    python manage.py import_destination_photos --apply    # simpan
"""

import re
import time

import requests
from django.core.management.base import BaseCommand, CommandError

from apps.gis.models import TouristDestination

SEARCH_URL = "https://commons.wikimedia.org/w/api.php"
# Wikimedia mewajibkan User-Agent deskriptif; UA bawaan python-requests di-403.
HEADERS = {
    "User-Agent": "TRIP/1.0 (VillageInsight DSS; photo import) python-requests"
}
STOPWORDS = {"the", "kota", "kabupaten", "desa", "park", "garden", "of", "and", "a", "an", "wisata", "alam"}


def _normalize(text):
    text = (text or "").lower()
    text = text.replace("file:", "")
    text = re.sub(r"\.(jpg|jpeg|png|svg|gif|webp)$", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _tokens(normalized):
    return [
        t for t in normalized.split()
        if (len(t) > 2 or t.isdigit()) and t not in STOPWORDS
    ]


def _is_confident(name_norm, title_norm):
    """True bila semua token penting nama destinasi ada di judul file."""
    name_tokens = _tokens(name_norm)
    if not name_tokens:
        return False
    title_tokens = set(_tokens(title_norm))
    return all(t in title_tokens for t in name_tokens)


def search_wikimedia(name):
    """Cari kandidat gambar di Wikimedia Commons.

    Return list [(title, url)] bila berhasil (mungkin kosong = tak ada hasil),
    atau None bila request gagal (mis. rate-limited) supaya bisa di-retry.
    """
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": name,
        "gsrnamespace": "6",  # File namespace (gambar)
        "gsrlimit": "5",
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": "800",
        "format": "json",
    }
    try:
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
    except (requests.RequestException, ValueError):
        return None

    results = []
    for page in pages.values():
        title = page.get("title", "")
        imageinfo = (page.get("imageinfo") or [{}])[0]
        # Buang query params (utm_...) supaya URL muat di URLField(max_length=200);
        # fallback ke URL asli (lebih pendek) bila thumbnail masih terlalu panjang.
        thumb = (imageinfo.get("thumburl") or "").split("?", 1)[0]
        original = (imageinfo.get("url") or "").split("?", 1)[0]
        url = thumb if len(thumb) <= 200 else (
            original if len(original) <= 200 else ""
        )
        if url:
            results.append((title, url))
    return results


class Command(BaseCommand):
    help = "Ambil foto destinasi dari Wikimedia Commons."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Simpan hasil ke database (default: dry-run).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Timpa foto yang sudah terisi.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        force = options["force"]

        qs = TouristDestination.objects.filter(is_active=True).order_by("name")
        if not force:
            qs = qs.filter(photo="")

        matched = 0
        skipped = 0
        failed = 0

        for dest in qs:
            name_norm = _normalize(dest.name)

            # Retry ringan bila Wikimedia me-rate-limit request.
            candidates = None
            for attempt in range(3):
                candidates = search_wikimedia(dest.name)
                if candidates is not None:
                    break
                time.sleep(1.5 * (attempt + 1))

            if candidates is None:
                failed += 1
                self.stdout.write(f"  ! {dest.name:<28} (request gagal)")
                continue

            chosen = None
            for title, url in candidates:
                if url and _is_confident(name_norm, _normalize(title)):
                    chosen = (title, url)
                    break

            if chosen is None:
                skipped += 1
                self.stdout.write(f"  - {dest.name:<28} (tidak ada foto cocok)")
            else:
                matched += 1
                self.stdout.write(
                    f"  + {dest.name:<28} -> {chosen[0]}"
                )
                if apply:
                    dest.photo = chosen[1]
                    dest.save(update_fields=["photo"])

            time.sleep(1.2)  # sopan ke API (hindari rate-limit)

        mode = "DISIMPAN" if apply else "DRY-RUN (belum disimpan)"
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: {matched} foto cocok, {skipped} dilewati, "
                f"{failed} gagal."
            )
        )
        if not apply:
            self.stdout.write(
                "Jalankan ulang dengan `--apply` untuk menyimpan ke database."
            )
