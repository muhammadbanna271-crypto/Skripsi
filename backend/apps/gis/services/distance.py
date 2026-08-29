"""
Utilitas jarak geografis.

Tahap awal memakai straight-line distance (haversine) karena routing engine
belum tersedia. Jarak ini adalah ESTIMASI geografis (garis lurus), BUKAN
waktu/jarak tempuh aktual. Arsitektur ini sengaja diisolasi di satu fungsi
supaya nanti mudah diganti dengan routing API (OSRM, Google, dsb.) tanpa
mengubah sistem utama.
"""

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Hitung jarak garis lurus (km) antara dua titik koordinat.

    Return None bila ada koordinat yang tidak valid/kosong.
    """

    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    try:
        lat1, lon1, lat2, lon2 = (
            float(lat1),
            float(lon1),
            float(lat2),
            float(lon2),
        )
    except (TypeError, ValueError):
        return None

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(EARTH_RADIUS_KM * c, 2)


def havsum(origin_lat, origin_lon, points):
    """
    Jarak total garis lurus origin -> tiap titik -> kembali ke origin (km).
    `points` adalah list of (lat, lon). Return None bila ada koordinat
    yang tidak valid.
    """

    if not points:
        return None

    if origin_lat is None or origin_lon is None:
        return None

    ordered = [(origin_lat, origin_lon)] + list(points) + [
        (origin_lat, origin_lon)
    ]

    total = 0.0

    for i in range(len(ordered) - 1):
        segment = haversine_km(
            ordered[i][0],
            ordered[i][1],
            ordered[i + 1][0],
            ordered[i + 1][1],
        )
        if segment is None:
            return None
        total += segment

    return round(total, 2)
