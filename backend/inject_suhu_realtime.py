"""
Inject data suhu real-time (Open-Meteo) ke GeoJSON batas desa Kota Batu.

Untuk tiap feature (desa):
- hitung centroid polygon (shapely),
- panggil Open-Meteo forecast (hourly temperature_2m, tz Asia/Jakarta),
- inject atribut suhu ke properties:
    * suhu_current      : suhu jam ini (°C)
    * suhu_siang_1200   : suhu jam 12:00 hari ini (°C)
    * suhu_malam_2400   : suhu jam 00:00 / tengah malam (°C)
    * hourly_temp_today : list 24 jam suhu hari ini (0..23)
    * last_updated      : ISO timestamp saat data diambil

Output: kota_batu_suhu_realtime_hourly.geojson
"""

import json
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from shapely.geometry import shape

INPUT = "C:/Agent/TRIP/backend/static/geo/batas_desa_kota_batu.geojson"
OUTPUT = "C:/Agent/TRIP/backend/static/geo/kota_batu_suhu_realtime_hourly.geojson"

API = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&hourly=temperature_2m"
    "&timezone=Asia%2FJakarta"
    "&past_days=1"
)

JAKARTA = ZoneInfo("Asia/Jakarta")


def round2(value):
    """Bulatkan ke 2 desimal; None bila kosong."""
    return round(float(value), 2) if value is not None else None


def fetch_today_hourly(lat, lon):
    """Ambil suhu per jam hari ini (dict hour->temp) + waktu sekarang."""
    url = API.format(lat=lat, lon=lon)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])

    now = datetime.now(JAKARTA)
    today = now.date()

    today_temps = {}
    for t, v in zip(times, temps):
        dt = datetime.fromisoformat(t)
        if dt.date() == today:
            today_temps[dt.hour] = v

    return now, today_temps


def main():
    data = json.load(open(INPUT, encoding="utf-8"))
    fetched_at = datetime.now(timezone.utc).isoformat()
    total = len(data["features"])

    for i, feature in enumerate(data["features"], 1):
        props = feature.setdefault("properties", {})
        name = props.get("village_name", "?")
        props["last_updated"] = fetched_at

        geom = shape(feature["geometry"])
        centroid = geom.centroid
        lat, lon = centroid.y, centroid.x

        try:
            now, today_temps = fetch_today_hourly(lat, lon)
            props["hourly_temp_today"] = [round2(today_temps.get(h)) for h in range(24)]
            props["suhu_current"] = round2(today_temps.get(now.hour))
            props["suhu_siang_1200"] = round2(today_temps.get(12))
            props["suhu_malam_2400"] = round2(today_temps.get(0))
            print(
                f"[{i:2d}/{total}] {name:18s} "
                f"cur={props['suhu_current']} 12:00={props['suhu_siang_1200']} "
                f"00:00={props['suhu_malam_2400']}"
            )
        except Exception as exc:
            print(f"[{i:2d}/{total}] {name:18s} ERROR: {exc}")
            props["hourly_temp_today"] = []
            props["suhu_current"] = None
            props["suhu_siang_1200"] = None
            props["suhu_malam_2400"] = None

        time.sleep(0.15)  # sopan ke API

    json.dump(data, open(OUTPUT, "w", encoding="utf-8"), ensure_ascii=False)
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
