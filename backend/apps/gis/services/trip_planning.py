"""
Trip Planning Engine — inti dari PRUDENCE sebagai dynamic trip planner.

Alur (bukan LLM mengarang bebas):

    parameter -> query database -> filter -> scoring/ranking
    -> itinerary generation -> estimasi biaya

Semua nilai yang keluar bersumber dari database (tiket, jam buka, koordinat,
kategori). Yang TIDAK ada di database dinyatakan "belum tersedia", tidak
dikarang. Jarak memakai haversine (garis lurus) dan selalu diberi label
"estimasi", karena routing engine belum tersedia.
"""

import logging
import time
from datetime import date, timedelta

from django.conf import settings

from apps.gis.models import TouristDestination
from apps.gis.services.distance import haversine_km, havsum

timing_logger = logging.getLogger("timing")


# Sinonim preferensi (Bahasa Indonesia <-> Inggris) untuk mencocokkan
# preferensi user dengan kategori/tourism_type yang tersimpan di database.
PREFERENCE_SYNONYMS = {
    "nature": ["alam", "nature", "panorama", "pegunungan"],
    "waterfall": ["air terjun", "waterfall", "coban"],
    "plantation": ["perkebunan", "plantation", "kebun"],
    "agriculture": ["pertanian", "agriculture", "sawah", "farm", "agrowisata"],
    "culture": ["budaya", "culture", "seni", "adat"],
    "education": ["edukasi", "education", "edukatif", "belajar"],
    "culinary": ["kuliner", "culinary", "makanan", "food", "oleh-oleh"],
    "family": ["keluarga", "family", "anak", "keluarga"],
    "adventure": ["petualangan", "adventure", "outbound", "tracking"],
    "history": ["sejarah", "history", "cagar", "heritage"],
    "religion": ["religi", "religion", "agama", "pesantren"],
    "photography": ["fotografi", "photography", "spot foto"],
    "outdoor": ["outdoor", "luar ruangan"],
    "indoor": ["indoor", "dalam ruangan"],
    "relax": ["relaksasi", "santai", "rileks", "pemandian"],
}

DIFFICULTY_SCORE = {
    "easy": 1.0,
    "moderate": 0.7,
    "hard": 0.35,
    "": 0.6,
}

DEFAULT_ORIGIN = {
    "name": "Alun-alun Kota Batu",
    "lat": -7.8695,
    "lon": 112.5236,
}


class TripPlanningService:
    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _weights():
        return dict(settings.GIS_TRIP_SCORING_WEIGHTS)

    @staticmethod
    def _transport_config(transportation):
        configs = settings.GIS_TRANSPORT_CONFIG
        return configs.get(
            transportation,
            configs.get("car", {}),
        )

    @staticmethod
    def _transport_config_for_vehicle(vehicle_type):
        """Map jenis kendaraan (Motor/Mobil/Bus/…) ke config bahan bakar."""
        key = {
            "motor": "motorcycle",
            "mobil": "car",
            "bus": "car",
            "pickup": "car",
            "minibus": "car",
        }.get(str(vehicle_type or "").strip().lower(), "car")
        return settings.GIS_TRANSPORT_CONFIG.get(key, {})

    @staticmethod
    def _per_person_budget(params):
        budget = params.get("budget")
        if budget in (None, 0, ""):
            return None
        try:
            budget = float(budget)
        except (TypeError, ValueError):
            return None
        scope = params.get("budget_scope", "total")
        count = params.get("traveler_count") or 1
        if scope == "per_person":
            return budget
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 1
        return budget / max(1, count)

    @staticmethod
    def _parse_date(value):
        """Parse 'YYYY-MM-DD' (str/date) -> date, atau None bila invalid."""
        if not value:
            return None
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value).strip())
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _is_weekend(day):
        return day.weekday() >= 5

    @classmethod
    def _trip_dates(cls, params):
        """List date untuk tiap hari trip, dari start_date + duration_days."""
        start = cls._parse_date(params.get("start_date"))
        if start is None:
            return []
        duration = int(params.get("duration_days") or 1)
        duration = max(1, min(duration, 7))
        return [start + timedelta(days=i) for i in range(duration)]

    @staticmethod
    def _expand_preference(pref):
        pref = (pref or "").strip().lower()
        if not pref:
            return []
        return list({pref, *PREFERENCE_SYNONYMS.get(pref, [])})

    @staticmethod
    def _destination_text(dest):
        categories = " ".join(
            category.name for category in dest.categories.all()
        )
        return " ".join(
            filter(
                None,
                [
                    dest.tourism_type or "",
                    categories,
                    dest.description or "",
                ],
            )
        ).lower()

    @classmethod
    def _query_destinations(cls):
        return (
            TouristDestination.objects
            .filter(is_active=True)
            .select_related("village", "district", "village__district")
            .prefetch_related(
                "categories",
                "cuisine_types",
                "wahanas",
                "wahanas__bundles",
                "bundles",
                "bundles__wahanas",
                "parking_fees",
            )
        )

    @classmethod
    def _matched_preferences(cls, text, prefs):
        """List preferensi yang cocok (untuk skor & alasan)."""
        matched = []
        for pref in prefs:
            terms = cls._expand_preference(pref)
            if any(term and term in text for term in terms):
                matched.append(pref)
        return matched

    # =========================================================
    # SCORING (transparan)
    # =========================================================

    @classmethod
    def _score_destination(cls, dest, params, origin, per_person_budget):
        text = cls._destination_text(dest)
        prefs = [p for p in (params.get("preferences") or []) if p]
        transportation = params.get("transportation") or ""
        elderly = bool(params.get("elderly"))
        children = bool(params.get("children"))

        factors = {}
        reasons = []

        # --- preference_match ---
        matched = cls._matched_preferences(text, prefs)
        if prefs:
            factors["preference_match"] = round(len(matched) / len(prefs), 3)
            for m in matched:
                reasons.append(f"cocok dengan preferensi \"{m}\"")
        else:
            factors["preference_match"] = 1.0

        # --- budget_compatibility ---
        ticket = dest.ticket_price_for(
            cls._parse_date(params.get("start_date"))
        )
        parking = dest.parking_cost_int
        cost = 0 if (ticket is None and parking is None) else (
            (ticket or 0) + (parking or 0)
        )
        if dest.is_free:
            factors["budget_compatibility"] = 1.0
            reasons.append("gratis (tanpa biaya tiket)")
        elif per_person_budget is None:
            factors["budget_compatibility"] = 0.5
        elif cost == 0 and ticket is None and parking is None:
            factors["budget_compatibility"] = 0.5
            reasons.append("harga tiket belum tersedia")
        else:
            ratio = cost / per_person_budget
            factors["budget_compatibility"] = round(
                max(0.0, min(1.0, 1.0 - ratio)), 3
            )
            if cost <= per_person_budget:
                reasons.append(
                    f"biaya masuk ±Rp{cost:,} sesuai anggaran per orang"
                )
            else:
                reasons.append(
                    f"biaya masuk ±Rp{cost:,} melebihi anggaran per orang"
                )

        # --- accessibility (difficulty + medan) ---
        acc = DIFFICULTY_SCORE.get(dest.difficulty or "", 0.6)
        if elderly and dest.elderly_friendly is False:
            acc *= 0.5
            reasons.append("kurang ramah untuk lansia")
        elif elderly and dest.elderly_friendly is None:
            acc *= 0.8
        if children and dest.child_friendly is False:
            acc *= 0.5
            reasons.append("kurang ramah untuk anak")
        elif children and dest.child_friendly is None:
            acc *= 0.8
        factors["accessibility"] = round(max(0.0, min(1.0, acc)), 3)

        # --- family/elderly suitability ---
        suit = 1.0
        if elderly:
            if dest.elderly_friendly is True:
                reasons.append("ramah untuk lansia")
                suit *= 1.0
            elif dest.elderly_friendly is False:
                suit *= 0.3
            else:
                suit *= 0.6
        if children:
            if dest.child_friendly is True:
                reasons.append("ramah untuk anak")
                suit *= 1.0
            elif dest.child_friendly is False:
                suit *= 0.3
            else:
                suit *= 0.6
        if dest.family_friendly is True and (elderly or children):
            suit = min(1.0, suit + 0.1)
            reasons.append("cocok untuk keluarga")
        factors["family_elderly_suitability"] = round(
            max(0.0, min(1.0, suit)), 3
        )

        # --- opening_hours ---
        if dest.opening_time and dest.closing_time:
            factors["opening_hours"] = 1.0
        elif dest.opening_time or dest.closing_time:
            factors["opening_hours"] = 0.6
        else:
            factors["opening_hours"] = 0.3

        # --- distance ---
        distance_km = None
        if (
            origin
            and dest.latitude is not None
            and dest.longitude is not None
        ):
            distance_km = haversine_km(
                origin["lat"],
                origin["lon"],
                float(dest.latitude),
                float(dest.longitude),
            )
        if distance_km is not None:
            factors["distance"] = round(
                max(0.0, min(1.0, 1.0 / (1.0 + distance_km / 10.0))), 3
            )
            reasons.append(f"±{distance_km} km dari titik awal")
        else:
            factors["distance"] = 0.5
            if origin:
                reasons.append("koordinat destinasi belum tersedia")

        weights = cls._weights()
        total = 0.0
        for key, weight in weights.items():
            total += weight * factors.get(key, 0.5)

        return {
            "score": round(total, 3),
            "factors": factors,
            "distance_km": distance_km,
            "cost": cost,
            "reasons": reasons[:5],
        }

    # =========================================================
    # SERIALIZE
    # =========================================================

    @staticmethod
    def _serialize_wahana(w):
        return {
            "id": w.id,
            "name": w.name,
            "pricing_type": w.pricing_type,
            "pricing_type_label": w.get_pricing_type_display(),
            "price": w.price_int,
            "price_display": w.price_display,
            "bundles": [b.name for b in w.bundles.all()],
            "is_active": w.is_active,
        }

    @staticmethod
    def _serialize_bundle(b):
        return {
            "id": b.id,
            "name": b.name,
            "price": b.price_int,
            "price_display": b.price_display,
            "includes_entry_ticket": b.includes_entry_ticket,
            "rides": [w.name for w in b.wahanas.all()],
            "is_active": b.is_active,
        }

    @staticmethod
    def _serialize_parking_fee(f):
        return {
            "vehicle_type": f.vehicle_type,
            "price": f.price_int,
            "price_display": f.price_display,
            "notes": f.notes,
            "is_active": f.is_active,
        }

    @classmethod
    def _serialize_destination(cls, dest):
        return {
            "id": dest.id,
            "name": dest.name,
            "village": dest.village.name if dest.village else None,
            "district": (
                dest.effective_district.name
                if dest.effective_district
                else None
            ),
            "tourism_type": dest.tourism_type or "",
            "place_type": dest.place_type,
            "categories": [c.name for c in dest.categories.all()],
            "cuisine_types": [c.name for c in dest.cuisine_types.all()],
            "price_min": int(dest.price_min) if dest.price_min is not None else None,
            "price_max": int(dest.price_max) if dest.price_max is not None else None,
            "price_range_display": dest.price_range_display,
            "ambiance": dest.ambiance or "",
            "description": dest.description or "",
            "ticket_price_weekday": dest.ticket_price_weekday_int,
            "ticket_price_weekend": dest.ticket_price_weekend_int,
            "parking_cost": dest.parking_cost_int,
            "is_free_parking": dest.is_free_parking,
            "parking_display": dest.parking_display,
            "estimated_duration_minutes": dest.estimated_duration_minutes,
            "opening_time": (
                dest.opening_time.strftime("%H:%M")
                if dest.opening_time
                else None
            ),
            "closing_time": (
                dest.closing_time.strftime("%H:%M")
                if dest.closing_time
                else None
            ),
            "closed_days": (
                list(dest.closed_days)
                if dest.closed_days is not None
                else None
            ),
            "closed_days_display": dest.closed_days_display,
            "is_open_every_day": dest.is_open_every_day,
            "is_open_24_hours": dest.is_open_24_hours,
            "operating_hours_display": dest.operating_hours_display,
            "difficulty": dest.difficulty or "",
            "family_friendly": dest.family_friendly,
            "elderly_friendly": dest.elderly_friendly,
            "child_friendly": dest.child_friendly,
            "indoor_outdoor": dest.indoor_outdoor or "",
            "elevation_meters": dest.elevation_meters,
            "elevation_source": dest.elevation_source or "",
            "temperature_c": dest.temperature_c,
            "temperature_source": dest.temperature_source or "",
            "temperature_date": (
                dest.temperature_date.isoformat()
                if dest.temperature_date
                else None
            ),
            "is_free": dest.is_free,
            "ticket_type": dest.ticket_type,
            "price_display": dest.price_display,
            "ride_prices_display": dest.ride_prices_display,
            "bundle_prices_display": dest.bundle_prices_display,
            "wahanas": [
                cls._serialize_wahana(w)
                for w in dest.active_wahanas
            ],
            "bundles": [
                cls._serialize_bundle(b)
                for b in dest.active_bundles
            ],
            "parking_fees": [
                cls._serialize_parking_fee(f)
                for f in dest.active_parking_fees
            ],
            "parking_fees_display": dest.parking_fees_display,
            "status": dest.status,
            "status_label": dest.status_label,
            "status_reason": dest.status_reason or "",
            "google_maps_url": dest.google_maps_url(),
            "google_maps_query": dest.effective_google_maps_query,
            "price_source": dest.price_source or "",
            "price_updated_at": (
                dest.price_updated_at.isoformat()
                if dest.price_updated_at
                else None
            ),
        }

    # =========================================================
    # SEARCH
    # =========================================================

    @classmethod
    def _resolve_origin(cls, params):
        origin = None
        if params.get("origin_lat") is not None and params.get("origin_lon") is not None:
            origin = {
                "lat": float(params["origin_lat"]),
                "lon": float(params["origin_lon"]),
            }
        elif params.get("use_default_origin", True):
            origin = DEFAULT_ORIGIN
        return origin

    @classmethod
    def search_destinations(cls, params):
        t0 = time.perf_counter()
        prefs = [p for p in (params.get("preferences") or []) if p]
        categories = [c for c in (params.get("categories") or []) if c]
        max_results = params.get("max_results") or 10
        start_date = cls._parse_date(params.get("start_date"))

        scored = []
        for scoring, dest in cls._ranked_destinations(params):
            data = cls._serialize_destination(dest)
            data.update(scoring)

            # Tandai apakah destinasi buka pada tanggal mulai (bila diberikan),
            # supaya LLM bisa memfilter. Tidak mengubah skor — trip bisa
            # berlangsung lebih dari satu hari.
            if start_date is not None:
                open_on_start = dest.is_open_on(start_date)
                data["open_on_start_date"] = open_on_start
                if open_on_start is False:
                    data["reasons"].append("tutup pada tanggal tersebut")

            scored.append(data)

        timing_logger.info(
            "search_destinations: %.0f ms (%d results)",
            (time.perf_counter() - t0) * 1000,
            len(scored),
        )

        return {
            "count": len(scored),
            "max_results": max_results,
            "filters": {
                "preferences": prefs,
                "categories": categories,
                "elderly": bool(params.get("elderly")),
                "children": bool(params.get("children")),
                "transportation": params.get("transportation"),
                "budget": params.get("budget"),
                "budget_scope": params.get("budget_scope", "total"),
            },
            "results": scored[:max_results],
        }

    # =========================================================
    # DETAIL
    # =========================================================

    @classmethod
    def get_destination_details(cls, destination_id=None, name=None):
        # Detail TIDAK difilter is_active: supaya chatbot bisa melihat status
        # & alasan destinasi nonaktif (mis. "sedang direnovasi") saat user
        # menanyakannya. Filtering active hanya untuk rekomendasi/itinerary.
        base_qs = (
            TouristDestination.objects
            .select_related("village", "district", "village__district")
            .prefetch_related(
                "categories",
                "cuisine_types",
                "wahanas",
                "wahanas__bundles",
                "bundles",
                "bundles__wahanas",
                "parking_fees",
            )
        )

        dest = None
        if destination_id is not None:
            dest = base_qs.filter(pk=destination_id).first()
        elif name:
            dest = base_qs.filter(name__iexact=name.strip()).first()
            if dest is None:
                dest = base_qs.filter(name__icontains=name.strip()).first()

        if dest is None:
            return {"found": False}

        data = cls._serialize_destination(dest)
        data["found"] = True
        data["accessibility"] = dest.accessibility or ""
        data["accessibility_details"] = dest.accessibility_details or {}
        data["facilities"] = dest.facilities or []
        data["source"] = dest.source or ""
        data["latitude"] = (
            float(dest.latitude) if dest.latitude is not None else None
        )
        data["longitude"] = (
            float(dest.longitude) if dest.longitude is not None else None
        )
        return data

    # =========================================================
    # ITINERARY
    # =========================================================

    @staticmethod
    def _format_time(minutes):
        minutes = int(round(minutes))
        hours = (minutes // 60) % 24
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    @classmethod
    def _order_route(cls, origin, dests):
        """
        Greedy nearest-neighbor dari titik awal — susun destinasi supaya
        jarak tempuh (garis lurus) mendekati minimal, tidak muter-muter.
        Destinasi tanpa koordinat ditaruh di akhir (tidak bisa dioptimasi).
        """
        if not origin:
            return list(dests), 0.0

        remaining = list(dests)
        ordered = []
        total_km = 0.0
        current = origin

        while remaining:
            best_index = None
            best_dist = None

            for i, d in enumerate(remaining):
                if d.latitude is None or d.longitude is None:
                    continue
                dist = haversine_km(
                    current["lat"],
                    current["lon"],
                    float(d.latitude),
                    float(d.longitude),
                )
                if dist is None:
                    continue
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_index = i

            if best_index is None:
                break

            chosen = remaining.pop(best_index)
            ordered.append(chosen)
            total_km += best_dist
            current = {
                "lat": float(chosen.latitude),
                "lon": float(chosen.longitude),
            }

        ordered.extend(remaining)
        return ordered, round(total_km, 2)

    @classmethod
    def build_itinerary(cls, params, destination_ids=None):
        t0 = time.perf_counter()
        duration_days = int(params.get("duration_days") or 1)
        duration_days = max(1, min(duration_days, 7))

        travelers = max(1, int(params.get("traveler_count") or 1))
        vehicles = params.get("vehicles") or []
        per_person_budget = cls._per_person_budget(params)
        primary_transport = (
            (vehicles[0].get("type") if vehicles else params.get("transportation"))
            or "car"
        )
        transport_cfg = cls._transport_config_for_vehicle(primary_transport)

        if destination_ids:
            ranked = cls._ranked_destinations(params, destination_ids)
        else:
            max_results = params.get("max_results") or 10
            ranked = cls._ranked_destinations(params)

        attractions = [d for _, d in ranked if d.place_type != "restaurant"]
        restaurants = [d for _, d in ranked if d.place_type == "restaurant"]
        if not destination_ids:
            attractions = attractions[:max_results]

        # Urutkan rute (nearest-neighbor) supaya tidak muter-muter.
        origin = cls._resolve_origin(params)
        attractions, route_km = cls._order_route(origin, attractions)

        day_start = settings.GIS_ITINERARY_DAY_START_MIN
        day_end = settings.GIS_ITINERARY_DAY_END_MIN
        lunch_start = settings.GIS_ITINERARY_LUNCH_START_MIN
        lunch_end = settings.GIS_ITINERARY_LUNCH_END_MIN
        lunch_duration = lunch_end - lunch_start

        days = []
        unscheduled = []
        current_day = []
        lunch_added = False
        clock = day_start
        current_location = origin
        used_types = set()
        total_cost = 0

        trip_dates = cls._trip_dates(params)

        def current_date():
            idx = len(days)
            if trip_dates and idx < len(trip_dates):
                return trip_dates[idx]
            return None

        def reset_day():
            nonlocal current_day, clock, lunch_added, used_types
            if current_day:
                days.append({"items": current_day})
            current_day = []
            clock = day_start
            lunch_added = False
            used_types = set()

        def dest_cost(dest):
            ticket = dest.ticket_price_for() or 0
            meal = cls._meal_cost(dest)
            parking_total = cls._parking_cost(dest, vehicles) or 0
            parking_per = parking_total / max(1, travelers)
            return ticket + meal + parking_per

        def pick_restaurant():
            def dist(r):
                if (
                    current_location
                    and r.latitude is not None
                    and r.longitude is not None
                ):
                    return haversine_km(
                        current_location["lat"],
                        current_location["lon"],
                        float(r.latitude),
                        float(r.longitude),
                    )
                return 9999

            # Filter jam buka: restaurant harus buka pada jam makan. Yang
            # hampir tutup (tutup sebelum jam makan selesai) diberi prioritas
            # rendah; yang jamnya belum diketahui tetap jadi kandidat.
            candidates = []
            for r in restaurants:
                if (
                    per_person_budget is not None
                    and cls._meal_cost(r) > per_person_budget
                ):
                    continue

                status = r.is_open_at_time(lunch_start)
                if status is False:
                    continue  # tutup pada jam makan -> jangan dipilih

                if status is None:
                    rank = 1  # jam buka belum diketahui
                elif r.closing_time is None:
                    rank = 0  # buka 24 jam (tidak ada jam tutup)
                else:
                    closing = (
                        r.closing_time.hour * 60 + r.closing_time.minute
                    )
                    # 0 = buka penuh, 2 = tutup sebelum jam makan selesai.
                    rank = 0 if closing >= lunch_end else 2

                candidates.append((r, rank))

            if not candidates:
                return None

            candidates.sort(key=lambda item: (item[1], dist(item[0])))
            return candidates[0][0]

        def lunch_item(restaurant, start_min):
            end_min = start_min + lunch_duration
            time_label = (
                f"{cls._format_time(start_min)} – {cls._format_time(end_min)}"
            )
            if restaurant is None:
                return {
                    "type": "lunch",
                    "time": time_label,
                    "name": "Makan siang / istirahat",
                    "duration_minutes": lunch_duration,
                    "restaurant_id": None,
                }
            return {
                "type": "lunch",
                "time": time_label,
                "name": restaurant.name,
                "restaurant_id": restaurant.id,
                "price_range": restaurant.price_range_display,
                "google_maps_url": restaurant.google_maps_url(),
                "duration_minutes": lunch_duration,
            }

        for dest in attractions:
            duration = cls._default_duration(dest)

            # Diversity: hindari tipe wisata yang sama dalam satu hari.
            dest_type = (dest.tourism_type or "").strip().lower()
            if dest_type and dest_type in used_types:
                unscheduled.append({
                    "name": dest.name,
                    "note": "mirip dengan destinasi lain di hari yang sama",
                })
                continue

            opening_min = None
            closing_min = None
            if dest.opening_time:
                opening_min = (
                    dest.opening_time.hour * 60 + dest.opening_time.minute
                )
            if dest.closing_time:
                closing_min = (
                    dest.closing_time.hour * 60 + dest.closing_time.minute
                )

            # Jadwal tutup: geser ke hari berikutnya bila tutup.
            closed_note = None
            while True:
                day_date = current_date()
                if day_date is None or dest.is_open_on(day_date) is not False:
                    break
                if len(days) < duration_days - 1:
                    reset_day()
                    continue
                closed_note = f"tutup pada {day_date.isoformat()}"
                break

            if closed_note is not None:
                unscheduled.append({"name": dest.name, "note": closed_note})
                continue

            # Sisipkan makan siang bila sudah tiba waktu makan (sebelum
            # berangkat ke destinasi berikutnya), memakai waktu AKTUAL supaya
            # tidak "nabrak" mundur. Lewati bila sudah lewat jendela makan.
            if not lunch_added and lunch_start <= clock < lunch_end:
                restaurant = pick_restaurant()
                current_day.append(lunch_item(restaurant, clock))
                if restaurant is not None:
                    total_cost += cls._meal_cost(restaurant) * travelers
                    if restaurant.latitude is not None and restaurant.longitude is not None:
                        current_location = {
                            "lat": float(restaurant.latitude),
                            "lon": float(restaurant.longitude),
                        }
                clock += lunch_duration
                lunch_added = True
            elif not lunch_added and clock >= lunch_end:
                # Sudah melewati jendela makan siang — lewati agar tidak nabrak.
                lunch_added = True

            # Waktu tempuh dari lokasi sebelumnya.
            clock += cls._travel_minutes(current_location, dest, transport_cfg)

            def try_place(day_clock):
                start = (
                    day_clock
                    if opening_min is None
                    else max(day_clock, opening_min)
                )
                if closing_min is not None and start >= closing_min:
                    return None
                end = start + duration
                if closing_min is not None and end > closing_min:
                    end = closing_min
                if end > day_end:
                    return None
                return start, end

            placed = try_place(clock)

            if placed is None and len(days) < duration_days - 1:
                reset_day()
                placed = try_place(clock)

            if placed is None:
                unscheduled.append({
                    "name": dest.name,
                    "note": "tidak muat di jadwal / di luar jam operasional",
                })
                continue

            start, end = placed

            # Budget hard constraint: lewati bila menambah melebihi budget.
            cost = dest_cost(dest)
            if (
                per_person_budget is not None
                and total_cost + cost * travelers > per_person_budget * travelers
            ):
                unscheduled.append({"name": dest.name, "note": "melebihi budget"})
                continue

            total_cost += cost * travelers

            note_parts = []
            if dest.opening_time is None or dest.closing_time is None:
                note_parts.append("jam buka belum tersedia")
            if dest.closed_days is None:
                note_parts.append("jadwal tutup belum diketahui")
            if dest.estimated_duration_minutes is None:
                note_parts.append("durasi kunjungan diasumsikan")

            current_day.append({
                "type": "destination",
                "time": f"{cls._format_time(start)} – {cls._format_time(end)}",
                "name": dest.name,
                "note": ", ".join(note_parts) if note_parts else "",
                "destination_id": dest.id,
                "duration_minutes": duration,
                "price_display": dest.price_display,
                "parking_display": dest.parking_display,
                "is_free_parking": dest.is_free_parking,
                "ride_prices_display": dest.ride_prices_display,
                "bundle_prices_display": dest.bundle_prices_display,
                "operating_hours": dest.operating_hours_display,
                "google_maps_url": dest.google_maps_url(),
                "status": dest.status,
                "ticket_type": dest.ticket_type,
            })

            clock = end + settings.GIS_ITINERARY_TRAVEL_BUFFER_MIN
            if dest_type:
                used_types.add(dest_type)
            if dest.latitude is not None and dest.longitude is not None:
                current_location = {
                    "lat": float(dest.latitude),
                    "lon": float(dest.longitude),
                }

        if current_day:
            days.append({"items": current_day})

        while len(days) < duration_days:
            days.append({"items": []})

        for index, day in enumerate(days, start=1):
            day["day"] = index

        # Estimasi bahan bakar (garis lurus) — dimasukkan ke total biaya.
        fuel = 0
        points = [
            (float(d.latitude), float(d.longitude))
            for d in attractions
            if d.latitude is not None and d.longitude is not None
        ]
        if origin and points:
            total_km = havsum(origin["lat"], origin["lon"], points)
            if total_km is not None:
                if vehicles:
                    for v in vehicles:
                        count = int(v.get("count") or 0)
                        cfg = cls._transport_config_for_vehicle(v.get("type"))
                        if count > 0 and cfg:
                            fuel += int(total_km * cfg.get("fuel_cost_per_km", 0)) * count
                else:
                    cfg = cls._transport_config(params.get("transportation") or "") or {}
                    fuel = int(total_km * cfg.get("fuel_cost_per_km", 0))

        total_cost += fuel
        budget_total = (
            per_person_budget * travelers
            if per_person_budget is not None
            else None
        )
        over_budget = budget_total is not None and total_cost > budget_total

        timing_logger.info(
            "build_itinerary: %.0f ms (%d days)",
            (time.perf_counter() - t0) * 1000,
            duration_days,
        )

        return {
            "duration_days": duration_days,
            "days": days[:duration_days],
            "unscheduled": unscheduled,
            "total_cost": total_cost,
            "budget": budget_total,
            "over_budget": over_budget,
            "route": {
                "method": "nearest-neighbor (garis lurus)",
                "total_km": route_km,
                "order": [
                    {
                        "name": d.name,
                        "village": d.village.name if d.village else None,
                    }
                    for d in attractions
                ],
                "note": (
                    "Urutan destinasi sudah dioptimasi supaya jarak tempuh "
                    "mendekati terpendek (tidak muter-muter). Estimasi "
                    "memakai garis lurus, bukan rute jalan aktual."
                ),
            },
            "note": (
                "Waktu mempertimbangkan jam buka, durasi kunjungan, dan "
                "perkiraan waktu tempuh (garis lurus). Destinasi yang mirip "
                "dihindari dalam satu hari, dan total biaya dijaga tidak "
                "melebihi budget bila budget diberikan."
            ),
        }

    # =========================================================
    # BUDGET
    # =========================================================

    @staticmethod
    def _parking_cost(dest, vehicles):
        """
        Total biaya parkir dari konfigurasi kendaraan (list {type, count}).
        Fallback ke harga tunggal legacy ``parking_cost_int`` bila tidak ada
        konfigurasi kendaraan atau tidak ada tarif yang cocok.
        """
        if not vehicles:
            return dest.parking_cost_int
        total = 0
        matched = False
        for v in vehicles:
            count = int(v.get("count") or 0)
            vtype = str(v.get("type") or "").strip()
            if count <= 0 or not vtype:
                continue
            fee = dest.parking_fee_for(vtype)
            if fee is None:
                continue
            matched = True
            total += count * fee
        return total if matched else dest.parking_cost_int

    @staticmethod
    def _min_cost(dest):
        """Biaya minimum per orang (untuk filter budget); None dianggap 0."""
        if dest.place_type == "restaurant":
            return int(dest.price_min or 0)
        ticket = dest.ticket_price_for() or 0
        parking = dest.parking_cost_int or 0
        return ticket + parking

    @staticmethod
    def _meal_cost(dest):
        """Estimasi biaya makan per orang (konservatif: pakai price_max)."""
        if dest.place_type != "restaurant":
            return 0
        if dest.price_max is not None:
            return int(dest.price_max)
        if dest.price_min is not None:
            return int(dest.price_min)
        return 0

    @staticmethod
    def _default_duration(dest):
        """Durasi kunjungan menit; default per tipe bila tidak diisi."""
        if dest.estimated_duration_minutes is not None:
            return dest.estimated_duration_minutes
        if dest.place_type == "restaurant":
            return 60
        ttype = (dest.tourism_type or "").lower()
        if "taman" in ttype or "rekreasi" in ttype or "park" in ttype:
            return 240
        if "museum" in ttype:
            return 90
        if "puncak" in ttype or "panorama" in ttype or "view" in ttype:
            return 60
        return settings.GIS_ITINERARY_DEFAULT_DURATION_MIN

    @staticmethod
    def _travel_minutes(origin, dest, transport_cfg):
        """Estimasi waktu tempuh (menit) dari koordinat, garis lurus."""
        if (
            origin is None
            or dest.latitude is None
            or dest.longitude is None
            or not transport_cfg
        ):
            return settings.GIS_ITINERARY_TRAVEL_BUFFER_MIN
        km = haversine_km(
            origin["lat"],
            origin["lon"],
            float(dest.latitude),
            float(dest.longitude),
        )
        speed = transport_cfg.get("avg_speed_kmh", 20) or 20
        return max(settings.GIS_ITINERARY_TRAVEL_BUFFER_MIN, int(round(km / speed * 60)))

    @classmethod
    def _ranked_destinations(cls, params, destination_ids=None, place_type=None):
        """
        Ambil kandidat destinasi (difilter budget bila diberikan), score, lalu
        urutkan. Return list tuple ``(scoring, dest)`` — dipakai search,
        build_itinerary, dan estimate_budget supaya TIDAK query ulang.
        ``place_type`` opsional untuk memisahkan attraction vs restaurant.
        """
        categories = [c for c in (params.get("categories") or []) if c]
        per_person_budget = cls._per_person_budget(params)
        origin = cls._resolve_origin(params)

        qs = cls._query_destinations()
        if destination_ids:
            qs = qs.filter(pk__in=destination_ids)
        if place_type:
            qs = qs.filter(place_type=place_type)
        if categories:
            qs = qs.filter(categories__name__in=categories).distinct()

        scored = []
        for dest in qs:
            # Hard constraint: destinasi yang sendirian sudah melebihi budget
            # per orang dilewati (filter deterministik, bukan brute-force).
            if (
                per_person_budget is not None
                and cls._min_cost(dest) > per_person_budget
            ):
                continue
            scoring = cls._score_destination(
                dest, params, origin, per_person_budget
            )
            scored.append((scoring, dest))

        scored.sort(key=lambda item: item[0]["score"], reverse=True)
        return scored

    @classmethod
    def estimate_budget(cls, params, destination_ids=None):
        t0 = time.perf_counter()
        if destination_ids:
            dests = [
                dest
                for _, dest in cls._ranked_destinations(params, destination_ids)
            ]
        else:
            max_results = params.get("max_results") or 10
            dests = [
                dest
                for _, dest in cls._ranked_destinations(params)[:max_results]
            ]

        known_breakdown = []
        unknown_items = []
        known_total = 0

        start_date = cls._parse_date(params.get("start_date"))
        vehicles = params.get("vehicles") or []
        travelers = max(1, int(params.get("traveler_count") or 1))
        per_person_budget = cls._per_person_budget(params)

        for dest in dests:
            # Restaurant dihitung sebagai biaya makan (range harga), bukan HTM.
            if dest.place_type == "restaurant":
                meal = cls._meal_cost(dest)
                known_breakdown.append({
                    "name": dest.name,
                    "place_type": "restaurant",
                    "meal": meal,
                    "price_range_display": dest.price_range_display,
                    "cuisine_types": [c.name for c in dest.cuisine_types.all()],
                    "ambiance": dest.ambiance or "",
                    "google_maps_url": dest.google_maps_url(),
                })
                known_total += meal * travelers
                continue

            weekday_price = dest.ticket_price_weekday_int
            weekend_price = dest.ticket_price_weekend_int
            parking = cls._parking_cost(dest, vehicles)

            wahanas = [
                cls._serialize_wahana(w)
                for w in dest.active_wahanas
            ]
            bundles = [
                cls._serialize_bundle(b)
                for b in dest.active_bundles
            ]

            # "Gratis" (is_free) dianggap DIKETAHUI (harga 0), BUKAN
            # "belum tersedia". Ini penting supaya tidak tercampur.
            has_price = (
                dest.is_free
                or weekday_price is not None
                or weekend_price is not None
                or parking is not None
                or dest.min_category_price is not None
            )

            # Destinasi tetap dimasukkan bila masih punya wahana/bundle,
            # meskipun harga tiket masuknya belum diketahui -- daftar wahana
            # berbayar tetap relevan untuk estimasi biaya. Hanya destinasi
            # yang benar-benar tanpa info harga apa pun yang dilewati.
            if not has_price and not wahanas and not bundles:
                unknown_items.append({
                    "name": dest.name,
                    "reason": "harga tiket & parkir belum tersedia",
                })
                continue

            ticket = dest.ticket_price_for(start_date)

            entry = {
                "name": dest.name,
                "ticket_weekday": weekday_price,
                "ticket_weekend": weekend_price,
                "ticket": ticket,
                "parking": parking,
                "is_free": dest.is_free,
                "is_free_parking": dest.is_free_parking,
                "parking_display": dest.parking_display,
                "ticket_type": dest.ticket_type,
                "price_display": dest.price_display,
                "ride_prices_display": dest.ride_prices_display,
                "bundle_prices_display": dest.bundle_prices_display,
                "wahanas": wahanas,
                "bundles": bundles,
                "parking_fees": [
                    cls._serialize_parking_fee(f)
                    for f in dest.active_parking_fees
                ],
                "google_maps_url": dest.google_maps_url(),
                "google_maps_query": dest.effective_google_maps_query,
            }
            known_breakdown.append(entry)
            known_total += (ticket or 0) + (parking or 0)

        # Estimasi transportasi (garis lurus), kalau koordinat tersedia.
        # Mendukung multi-kendaraan (vehicles) atau satu moda (transportation).
        origin = cls._resolve_origin(params)
        vehicles = params.get("vehicles") or []

        transport_estimate = None
        transport_label = "tidak ditentukan"

        points = [
            (float(d.latitude), float(d.longitude))
            for d in dests
            if d.latitude is not None and d.longitude is not None
        ]
        total_km = (
            havsum(origin["lat"], origin["lon"], points)
            if (origin and points)
            else None
        )

        if total_km is not None:
            if vehicles:
                fuel_cost = 0
                labels = []
                for v in vehicles:
                    count = int(v.get("count") or 0)
                    if count <= 0:
                        continue
                    cfg = cls._transport_config_for_vehicle(v.get("type"))
                    rate = cfg.get("fuel_cost_per_km", 0)
                    fuel_cost += int(total_km * rate) * count
                    labels.append(
                        f"{count} {cfg.get('label', v.get('type') or 'kendaraan')}"
                    )
                transport_estimate = {
                    "distance_km": total_km,
                    "fuel_cost_per_km": None,
                    "fuel_cost": fuel_cost,
                    "label": (
                        "Estimasi bahan bakar " + ", ".join(labels)
                        + " (garis lurus, bukan jarak tempuh aktual)"
                    ),
                }
                transport_label = ", ".join(labels)
            else:
                transport_name = params.get("transportation") or ""
                transport_cfg = (
                    cls._transport_config(transport_name)
                    if transport_name
                    else None
                )
                if transport_cfg:
                    fuel_per_km = transport_cfg.get("fuel_cost_per_km", 0)
                    fuel_cost = int(total_km * fuel_per_km)
                    transport_estimate = {
                        "distance_km": total_km,
                        "fuel_cost_per_km": fuel_per_km,
                        "fuel_cost": fuel_cost,
                        "label": (
                            f"Estimasi bahan bakar {transport_cfg.get('label', '')}"
                            f" (garis lurus, bukan jarak tempuh aktual)"
                        ),
                    }
                    transport_label = transport_cfg["label"]

        fuel_cost = transport_estimate.get("fuel_cost") if transport_estimate else 0
        grand_total = known_total + (fuel_cost or 0)
        budget_total = (
            per_person_budget * travelers
            if per_person_budget is not None
            else None
        )
        over_budget = budget_total is not None and grand_total > budget_total

        timing_logger.info(
            "estimate_budget: %.0f ms (%d known)",
            (time.perf_counter() - t0) * 1000,
            len(known_breakdown),
        )

        return {
            "known_total": known_total,
            "grand_total": grand_total,
            "budget": budget_total,
            "over_budget": over_budget,
            "known_breakdown": known_breakdown,
            "unknown_items": unknown_items,
            "transportation": transport_label,
            "transport_estimate": transport_estimate,
            "label": "Estimasi berdasarkan data yang tersedia.",
            "note": (
                "Total menjumlahkan tiket, makan (range harga restaurant), "
                "parkir, dan estimasi bahan bakar yang diketahui. Harga tiket "
                "dibedakan weekday (Senin–Jumat) dan weekend (Sabtu–Minggu); "
                "biaya yang belum tersedia tidak diikutsertakan."
            ),
        }
