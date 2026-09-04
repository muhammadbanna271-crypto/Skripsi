"""Palet warna cluster terpusat (single source of truth).

Satu-satunya tempat warna cluster didefinisikan. Dipakai oleh BOTH:
- cluster desa (K-Means, ``apps.master.models.Cluster``), dan
- kelas LCA responden (hasil pipeline ``survey_analysis``),

supaya warna yang sama konsisten di semua visualisasi (pie, scatter, tabel,
badge, bar, legend). JANGAN hardcode warna cluster di tempat lain.

Palet: Okabe-Ito (2008) — colorblind-friendly, aman untuk protanopia /
deuteranopia. Hex diambil apa adanya (palet teruji), hanya diurutkan ulang agar
warna paling kontras muncul lebih dulu di latar putih.
"""

# Okabe-Ito 8 warna (urutan dioptimalkan untuk kontras).
CLUSTER_PALETTE = [
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#009E73",  # bluish green
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#CC79A7",  # reddish purple
    "#F0E442",  # yellow
    "#000000",  # black
]

# Warna netral untuk entitas yang belum terklasifikasi (bukan bagian palet).
UNASSIGNED_COLOR = "#6c757d"


def color_for_index(index):
    """Warna palet untuk index (0-based); cyclic bila index melebihi palet."""
    return CLUSTER_PALETTE[index % len(CLUSTER_PALETTE)]


def cluster_color_map():
    """Map ``{cluster.name: hex}`` berdasar urutan ``code`` yang stabil.

    Urutan ``order_by("code")`` menjamin cluster yang sama selalu mendapat
    warna yang sama, meskipun urutan query/data berubah atau ada filter aktif.
    """
    from apps.master.models import Cluster

    clusters = list(Cluster.objects.order_by("code"))
    return {
        cluster.name: color_for_index(i)
        for i, cluster in enumerate(clusters)
    }
