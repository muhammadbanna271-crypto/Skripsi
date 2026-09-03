"""Konfigurasi model SEM (konstruk + jalur struktural).

Disimpan terpisah dari kode supaya nama konstruk, indikator, maupun jalur
(panah) dapat diubah TANPA mengubah kode analisis. Konstruk di sini adalah
konstruk LATEN — setiap konstruk diukur oleh beberapa item Likert (indikator),
bukan item kuesioner tunggal.

Struktur (mengikuti diagram):
- Eksogen (X): X1..X5
- Mediator (Y): Y1..Y3
- Outcome (Z): Z1..Z3   (di diagram disebut Y4..Y6)

Jalur struktural: full mesh X -> Y (15 jalur) dan Y -> Z (9 jalur),
TANPA jalur langsung X -> Z (full mediation).
"""

# ---------- Konstruk laten ----------
# role: "exogenous" | "mediator" | "outcome"
# items: kode indikator Likert yang mengukur konstruk (item kuesioner).
CONSTRUCTS = {
    "X1": {
        "name": "Orientasi Pasar",
        "role": "exogenous",
        "items": ["X1.1", "X1.2", "X1.3", "X1.4", "X1.5", "X1.6", "X1.7", "X1.8"],
    },
    "X2": {
        "name": "Fasilitas Pariwisata",
        "role": "exogenous",
        "items": ["X2.1", "X2.2", "X2.3", "X2.4", "X2.5", "X2.6", "X2.7", "X2.8"],
    },
    "X3": {
        "name": "Infrastruktur dan Aksesibilitas",
        "role": "exogenous",
        "items": ["X3.1", "X3.2", "X3.3", "X3.4", "X3.5", "X3.6", "X3.7", "X3.8"],
    },
    "X4": {
        "name": "Hubungan Pemasaran",
        "role": "exogenous",
        "items": ["X4.1", "X4.2", "X4.3", "X4.4", "X4.5", "X4.6", "X4.7", "X4.8"],
    },
    "X5": {
        "name": "Kepuasan Pengunjung",
        "role": "exogenous",
        "items": ["X5.1", "X5.2", "X5.3", "X5.4", "X5.5", "X5.6", "X5.7", "X5.8"],
    },
    "Y1": {
        "name": "Inovasi Ekonomi Kreatif",
        "role": "mediator",
        "items": ["Y1.1", "Y1.2", "Y1.3", "Y1.4", "Y1.5", "Y1.6", "Y1.7", "Y1.8"],
    },
    "Y2": {
        "name": "Kualitas Layanan",
        "role": "mediator",
        "items": ["Y2.1", "Y2.2", "Y2.3", "Y2.4", "Y2.5", "Y2.6", "Y2.7", "Y2.8"],
    },
    "Y3": {
        "name": "Orientasi Kewirausahaan",
        "role": "mediator",
        "items": ["Y3.1", "Y3.2", "Y3.3", "Y3.4", "Y3.5", "Y3.6", "Y3.7", "Y3.8"],
    },
    "Z1": {
        "name": "Penerimaan Daerah",
        "role": "outcome",
        "items": ["Z1.1", "Z1.2", "Z1.3", "Z1.4", "Z1.5", "Z1.6", "Z1.7", "Z1.8"],
    },
    "Z2": {
        "name": "Kunjungan Wisata",
        "role": "outcome",
        "items": ["Z2.1", "Z2.2", "Z2.3", "Z2.4", "Z2.5", "Z2.6", "Z2.7", "Z2.8"],
    },
    "Z3": {
        "name": "Keunggulan Bersaing",
        "role": "outcome",
        "items": ["Z3.1", "Z3.2", "Z3.3", "Z3.4", "Z3.5", "Z3.6", "Z3.7", "Z3.8"],
    },
}

# ---------- Kelompok peran (untuk menurunkan jalur) ----------
EXOGENOUS = ["X1", "X2", "X3", "X4", "X5"]
MEDIATORS = ["Y1", "Y2", "Y3"]
OUTCOMES = ["Z1", "Z2", "Z3"]

# ---------- Jalur struktural (arah panah) ----------
# Full mesh: X -> Y (15) + Y -> Z (9) = 24 jalur. TANPA X -> Z langsung.
# Untuk menghapus/menambah satu jalur tertentu, ganti PATHS dengan daftar
# eksplisit, mis. PATHS = [("X1","Y1"), ("X2","Y2"), ("Y1","Z1"), ...].
PATHS = (
    [(x, y) for x in EXOGENOUS for y in MEDIATORS]
    + [(y, z) for y in MEDIATORS for z in OUTCOMES]
)

# ---------- Reverse-coded items ----------
# BELUM DIKONFIRMASI. Kosongkan = tidak ada reverse coding otomatis.
# Jika ada, isi kode item, mis. REVERSE_ITEMS = ["X1.5", "Y2.3"].
REVERSE_ITEMS = []


def _construct_sort_key(code):
    """Urutkan konstruk sebagai X1..X5, Y1..Y3, Z1..Z3."""
    group = code[0]
    num = int(code[1:])
    group_order = {"X": 0, "Y": 1, "Z": 2}
    return (group_order.get(group, 9), num)


def construct_order():
    """Kode konstruk terurut (X1..X5, Y1..Y3, Z1..Z3)."""
    return sorted(CONSTRUCTS, key=_construct_sort_key)


def all_items():
    """Semua kode item Likert, urut sesuai urutan konstruk."""
    out = []
    for code in construct_order():
        out.extend(CONSTRUCTS[code]["items"])
    return out


def role_of(code):
    return CONSTRUCTS[code]["role"]


def name_of(code):
    return CONSTRUCTS[code]["name"]
