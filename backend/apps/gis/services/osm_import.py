"""
Import destinasi wisata Kota Batu dari OpenStreetMap (Overpass API).

Sumber: OpenStreetMap (ODbL). Data diambil dari node/way/relation bertag
wisata (tourism/natural/leisure/historic/amenity/attraction) di dalam
bounding box Kota Batu. Hari tutup digali dari tag ``opening_hours``.

Prinsip project: TIDAK mengarang. Yang tidak bisa diparse dibiarkan
None/"belum diketahui". Harga tiket sengaja TIDAK diisi (tag ``charge`` OSM
jarang terisi untuk destinasi Indonesia dan formatnya tidak konsisten).
"""

import re
from datetime import time

import requests

from apps.gis.services.distance import haversine_km
from apps.master.models import Village


OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# key -> regex value yang dianggap "wisata". Urutan menentukan prioritas
# tourism_type (yang lebih dulu cocok menang).
KEY_VALUES = [
    ("tourism", "theme_park|attraction|museum|zoo|viewpoint|gallery|picnic_site"),
    ("natural", "waterfall|peak|volcano|spring|cave_entrance|beach"),
    ("leisure", "park|garden|water_park|nature_reserve"),
    ("historic", "monument|memorial|ruins|castle|archaeological_site|fort|city_gate"),
    ("amenity", "theme_park|water_park|museum"),
    ("attraction", "animal|water_slide|roller_coaster|summer_toboggan|maze|big_wheel"),
]

# (key, value) -> (tourism_type, [kategori]). Kategori memakai nama yang
# cocok dengan PREFERENCE_SYNONYMS di trip_planning supaya scoring jalan.
TYPE_MAP = {
    ("tourism", "theme_park"): ("taman rekreasi", ["keluarga", "taman rekreasi"]),
    ("tourism", "attraction"): ("wisata", ["alam"]),
    ("tourism", "museum"): ("museum", ["edukasi", "museum", "sejarah"]),
    ("tourism", "zoo"): ("kebun binatang", ["keluarga", "edukasi"]),
    ("tourism", "viewpoint"): ("panorama", ["alam", "fotografi", "panorama"]),
    ("tourism", "gallery"): ("galeri seni", ["budaya", "edukasi"]),
    ("tourism", "picnic_site"): ("area piknik", ["keluarga", "alam"]),
    ("natural", "waterfall"): ("air terjun", ["alam", "air terjun"]),
    ("natural", "peak"): ("puncak", ["alam", "petualangan"]),
    ("natural", "volcano"): ("gunung", ["alam", "petualangan"]),
    ("natural", "spring"): ("mata air", ["alam"]),
    ("natural", "cave_entrance"): ("gua", ["alam", "petualangan"]),
    ("natural", "beach"): ("pantai", ["alam", "keluarga"]),
    ("leisure", "park"): ("taman", ["keluarga", "alam"]),
    ("leisure", "garden"): ("taman", ["alam", "fotografi"]),
    ("leisure", "water_park"): ("waterpark", ["keluarga", "taman rekreasi"]),
    ("leisure", "nature_reserve"): ("cagar alam", ["alam", "petualangan"]),
    ("historic", "monument"): ("monumen", ["sejarah", "budaya"]),
    ("historic", "memorial"): ("monumen", ["sejarah", "budaya"]),
    ("historic", "ruins"): ("situs sejarah", ["sejarah", "budaya"]),
    ("historic", "castle"): ("bangunan bersejarah", ["sejarah", "budaya"]),
    ("historic", "archaeological_site"): ("situs arkeologi", ["sejarah", "edukasi"]),
    ("historic", "fort"): ("benteng", ["sejarah"]),
    ("historic", "city_gate"): ("situs sejarah", ["sejarah"]),
    ("amenity", "theme_park"): ("taman rekreasi", ["keluarga", "taman rekreasi"]),
    ("amenity", "water_park"): ("waterpark", ["keluarga"]),
    ("amenity", "museum"): ("museum", ["edukasi", "museum"]),
    ("attraction", "animal"): ("taman hewan", ["keluarga", "edukasi"]),
    ("attraction", "water_slide"): ("waterpark", ["keluarga"]),
    ("attraction", "roller_coaster"): ("taman rekreasi", ["keluarga", "petualangan"]),
    ("attraction", "summer_toboggan"): ("taman rekreasi", ["keluarga", "petualangan"]),
    ("attraction", "maze"): ("taman rekreasi", ["keluarga"]),
    ("attraction", "big_wheel"): ("taman rekreasi", ["keluarga"]),
}

DAY_INDEX = {"mo": 0, "tu": 1, "we": 2, "th": 3, "fr": 4, "sa": 5, "su": 6}
TIME_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")


# =========================================================
# OVERPASS QUERY
# =========================================================

def build_overpass_query(bbox):
    """bbox = (south, west, north, east). Return query QL string."""
    south, west, north, east = bbox
    lines = ["[out:json][timeout:120];", "("]
    for key, values in KEY_VALUES:
        lines.append(
            f'  nwr["{key}"~"^({values})$"]({south},{west},{north},{east});'
        )
    lines.append(");")
    lines.append("out center tags;")
    return "\n".join(lines)


def fetch_osm_destinations(bbox):
    """Ambil elemen OSM untuk bbox. Return list of dict."""
    query = build_overpass_query(bbox)
    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        timeout=120,
        headers={"User-Agent": "trip-scraper/1.0"},
    )
    response.raise_for_status()
    return response.json().get("elements", [])


# =========================================================
# PARSING OPENING_HOURS
# =========================================================

def _parse_dayspec(spec):
    """
    'Mo-Fr', 'Sa,Su', 'Mo-We,Fr', 'Mo-Su', 'Tu' -> set int hari (0..6).
    'PH'/'SH' diabaikan.
    """
    days = set()
    for part in spec.split(","):
        part = part.strip().lower()
        if not part or part in ("ph", "sh"):
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = a.strip(), b.strip()
            if a not in DAY_INDEX or b not in DAY_INDEX:
                continue
            start, end = DAY_INDEX[a], DAY_INDEX[b]
            if start <= end:
                days.update(range(start, end + 1))
            else:
                # wrap: mis. Sa-Mo -> Sabtu, Minggu, Senin
                days.update(range(start, 7))
                days.update(range(0, end + 1))
        elif part in DAY_INDEX:
            days.add(DAY_INDEX[part])
    return days


def parse_opening_hours(value):
    """
    Parse tag ``opening_hours`` OSM -> (closed_days, opening_min, closing_min).

    - closed_days : list int (0=Senin..6=Minggu), atau None bila tidak bisa
      diketahui. ``[]`` artinya buka setiap hari.
    - opening_min / closing_min : int menit sejak 00:00, atau None.
    """
    if not value:
        return None, None, None

    text = value.strip().lower()
    if text in ("24/7", "00:00-24:00", "always", "sunrise-sunset"):
        return [], None, None

    days_open = set()
    starts = []
    ends = []

    for rule in text.split(";"):
        rule = rule.strip()
        if not rule:
            continue

        digit = re.search(r"\d", rule)
        if digit is None:
            continue

        dayspec = rule[: digit.start()].strip().strip(":,")
        timespec = rule[digit.start():].strip()

        if not dayspec:
            days_open.update(range(7))
        else:
            parsed = _parse_dayspec(dayspec)
            if not parsed:
                # hanya PH/SH atau tidak dikenali -> lewati rule ini.
                continue
            days_open.update(parsed)

        for match in TIME_RANGE_RE.finditer(timespec):
            h1, m1, h2, m2 = (int(x) for x in match.groups())
            starts.append(h1 * 60 + m1)
            ends.append(h2 * 60 + m2)

    if not days_open:
        return None, None, None

    closed = [d for d in range(7) if d not in days_open]
    opening_min = min(starts) if starts else None
    closing_min = max(ends) if ends else None
    return closed, opening_min, closing_min


# =========================================================
# MAPPING TAG -> tourism_type + kategori
# =========================================================

def map_tourism_type(tags):
    """Return (tourism_type, [category_names]). (None, []) bila tak dikenal."""
    for key, _values in KEY_VALUES:
        value = tags.get(key)
        if not value:
            continue
        hit = TYPE_MAP.get((key, value))
        if hit:
            return hit
        return value, []
    return None, []


# =========================================================
# GEOSPASIAL
# =========================================================

def element_coords(element):
    lat = element.get("lat")
    lon = element.get("lon")
    if lat is None or lon is None:
        center = element.get("center") or {}
        lat = center.get("lat")
        lon = center.get("lon")
    if lat is None or lon is None:
        return None, None
    return float(lat), float(lon)


def nearest_village(lat, lon, max_km=12.0):
    """Desa terdekat dari (lat, lon). Return (village|None, km|None)."""
    villages = list(
        Village.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
        )
    )
    best = None
    best_km = None
    for village in villages:
        km = haversine_km(lat, lon, village.latitude, village.longitude)
        if km is None:
            continue
        if best_km is None or km < best_km:
            best_km = km
            best = village

    if best is None:
        return None, None
    if max_km is not None and best_km > max_km:
        return None, best_km
    return best, best_km


# =========================================================
# UTIL
# =========================================================

def minutes_to_time(minutes):
    if minutes is None:
        return None
    minutes = int(minutes)
    return time(hour=(minutes // 60) % 24, minute=minutes % 60)


def element_score(element):
    """Skor 'kelengkapan' elemen untuk dedupe nama ganda di OSM."""
    tags = element.get("tags") or {}
    score = len(tags)
    if tags.get("opening_hours"):
        score += 5
    if element.get("type") == "relation":
        score += 2
    elif element.get("type") == "way":
        score += 1
    return score


def dedupe_by_name(elements):
    """Simpan satu elemen per nama (casefold), pilih yang paling lengkap."""
    best = {}
    for element in elements:
        name = ((element.get("tags") or {}).get("name") or "").strip()
        if not name:
            continue
        key = name.casefold()
        if key not in best or element_score(element) > element_score(best[key]):
            best[key] = element
    return list(best.values())
