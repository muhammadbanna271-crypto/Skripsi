"""
GeoJSON service — membaca batas wilayah (GeoJSON) lalu me-merge data dari
database (cluster, elevasi, karakteristik, skor, jumlah destinasi) ke tiap
feature, sehingga peta tidak menyimpan data secara hard-code.

Semua data tambahan diambil dari database sebagai source of truth. Jika
file GeoJSON resmi belum dimasukkan, endpoint mengembalikan FeatureCollection
kosong + status, BUKAN polygon/koordinat palsu.
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count

from apps.analytics.models import MLModelRegistry
from apps.gis.models import (
    RegionCharacteristic,
    RegionElevation,
    TouristDestination,
)
from apps.master.models import Cluster, Village
from apps.recommendation.models import RecommendationResult


DEFAULT_CLUSTER_COLOR = "#0d6efd"


class GeoJSONService:
    # =========================================================
    # FILE LOADING
    # =========================================================

    @classmethod
    def geojson_path(cls):
        path = Path(settings.BASE_DIR) / settings.GIS_GEOJSON_PATH
        return path

    @classmethod
    def load_features(cls):
        """
        Baca file GeoJSON. Return (features, note).

        features : list of feature dict (kosong bila file belum ada/invalid)
        note     : None bila berhasil, string penjelasan bila tidak.
        """
        path = cls.geojson_path()

        if not path.exists():
            return [], (
                "File GeoJSON batas desa belum tersedia "
                f"({path.name})."
            )

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return [], "File GeoJSON tidak dapat dibaca (format tidak valid)."

        if not isinstance(data, dict):
            return [], "Format GeoJSON tidak valid."

        features = data.get("features", [])

        if not isinstance(features, list):
            return [], "Format GeoJSON tidak valid (features bukan list)."

        return features, None

    # =========================================================
    # LOOKUP VILLAGE (sekali query, tanpa N+1)
    # =========================================================

    @classmethod
    def _village_lookup(cls):
        villages = list(
            Village.objects
            .select_related(
                "district",
                "cluster",
                "village_score",
                "elevation",
            )
            .prefetch_related("characteristics")
            .annotate(destination_count=Count("destinations", distinct=True))
        )

        by_id = {}
        by_code = {}
        by_name = {}

        for village in villages:
            by_id[village.id] = village
            if village.code:
                by_code[village.code] = village
            by_name[village.name.lower()] = village

        return {
            "by_id": by_id,
            "by_code": by_code,
            "by_name": by_name,
        }

    @classmethod
    def _recommendation_lookup(cls):
        cached = RecommendationResult.objects.order_by("-computed_at").first()
        if cached is None:
            return {}
        return {
            item.get("village_id"): item
            for item in (cached.ranking or [])
            if isinstance(item, dict)
        }

    # =========================================================
    # CLUSTER LEGEND
    # =========================================================

    @classmethod
    def cluster_legend(cls):
        """Daftar cluster (yang punya desa) + warna dinamis + statistik."""
        clusters = list(
            Cluster.objects
            .filter(villages__isnull=False)
            .distinct()
            .order_by("code")
        )

        registry = (
            MLModelRegistry.objects.filter(is_active=True).first()
        )

        mapping = {}
        if registry and isinstance(registry.cluster_mapping, dict):
            for label, info in registry.cluster_mapping.items():
                if isinstance(info, dict) and info.get("cluster_id"):
                    mapping[info["cluster_id"]] = info

        palette = list(settings.GIS_CLUSTER_PALETTE)

        result = []
        used_colors = set()

        for index, cluster in enumerate(clusters):
            custom = (cluster.color or "").strip().lower()

            if (
                custom
                and custom != DEFAULT_CLUSTER_COLOR
                and custom not in used_colors
            ):
                color = cluster.color
            else:
                color = palette[index % len(palette)]

            used_colors.add(color)

            info = mapping.get(cluster.id, {})

            result.append({
                "id": cluster.id,
                "code": cluster.code,
                "name": cluster.name,
                "color": color,
                "count": cluster.villages.count(),
                "rank": info.get("rank"),
                "mean_score": info.get("mean_score"),
                "description": cluster.description,
            })

        return result

    # =========================================================
    # ELEVATION CLASSES
    # =========================================================

    @classmethod
    def elevation_classes(cls):
        return list(settings.GIS_ELEVATION_CLASSES)

    # =========================================================
    # CHARACTERISTICS OPTIONS (untuk layer karakteristik)
    # =========================================================

    @classmethod
    def characteristic_options(cls):
        rows = (
            RegionCharacteristic.objects
            .values("characteristic_type", "characteristic_name", "value_type")
            .distinct()
            .order_by("characteristic_type", "characteristic_name")
        )
        return [
            {
                "type": row["characteristic_type"],
                "name": row["characteristic_name"],
                "value_type": row["value_type"],
            }
            for row in rows
        ]

    # =========================================================
    # SERIALIZE VILLAGE -> PROPERTIES
    # =========================================================

    @classmethod
    def _village_properties(cls, village, rec=None):
        cluster = village.cluster
        elevation = getattr(village, "elevation", None)
        score = getattr(village, "village_score", None)

        props = {
            "village_id": village.id,
            "village_name": village.name,
            "village_code": village.code,
            "district_id": village.district_id,
            "district_name": (
                village.district.name if village.district else None
            ),
            "description": village.description or "",
            "latitude": (
                float(village.latitude) if village.latitude is not None else None
            ),
            "longitude": (
                float(village.longitude)
                if village.longitude is not None
                else None
            ),
            "cluster": {
                "id": cluster.id,
                "code": cluster.code,
                "name": cluster.name,
            } if cluster else None,
            "elevation": {
                "min": elevation.min_elevation,
                "max": elevation.max_elevation,
                "mean": elevation.mean_elevation,
                "median": elevation.median_elevation,
                "std": elevation.std_deviation,
                "range": elevation.range_meters,
                "source": elevation.source_dataset or "",
            } if elevation is not None else None,
            "characteristics": [
                {
                    "type": c.characteristic_type,
                    "name": c.characteristic_name,
                    "value": c.value,
                    "value_type": c.value_type,
                    "source": c.source or "",
                }
                for c in village.characteristics.all()
            ],
            "destination_count": getattr(village, "destination_count", 0),
            "score": {
                "total_score": float(score.total_score) if score else None,
                "normalized_score": (
                    float(score.normalized_score) if score else None
                ),
                "rank": score.rank if score else None,
            } if score is not None else None,
        }

        if rec:
            props["recommendation"] = {
                "status": rec.get("status"),
                "recommendation": rec.get("recommendation"),
            }

        return props

    # =========================================================
    # VILLAGE GEOJSON
    # =========================================================

    @classmethod
    def village_geojson(cls):
        features, note = cls.load_features()

        lookup = cls._village_lookup()
        rec_lookup = cls._recommendation_lookup()

        enriched = []

        for feature in features:
            props = feature.get("properties") or {}
            village = None

            village_id = props.get("village_id")
            village_code = props.get("village_code")
            village_name = props.get("village_name")

            if village_id in lookup["by_id"]:
                village = lookup["by_id"][village_id]
            elif village_code and village_code in lookup["by_code"]:
                village = lookup["by_code"][village_code]
            elif village_name and village_name.lower() in lookup["by_name"]:
                village = lookup["by_name"][village_name.lower()]

            if village is None:
                # Polygon tidak punya desa di DB: tetap ikut (dengan properti
                # aslinya) supaya tidak hilang dari peta, tapi tanpa data DB.
                enriched.append({
                    "type": feature.get("type", "Feature"),
                    "geometry": feature.get("geometry"),
                    "properties": {
                        **props,
                        "matched": False,
                    },
                })
                continue

            merged_props = {
                **props,
                **cls._village_properties(village, rec_lookup.get(village.id)),
                "matched": True,
            }

            enriched.append({
                "type": feature.get("type", "Feature"),
                "geometry": feature.get("geometry"),
                "properties": merged_props,
            })

        return {
            "type": "FeatureCollection",
            "features": enriched,
            "status": {
                "has_geojson": len(features) > 0,
                "note": note,
                "matched": sum(
                    1 for f in enriched if f["properties"].get("matched")
                ),
            },
        }

    # =========================================================
    # VILLAGE POINTS (fallback titik pusat desa, bila tidak ada polygon)
    # =========================================================

    @classmethod
    def village_points_geojson(cls):
        villages = list(
            Village.objects
            .filter(latitude__isnull=False, longitude__isnull=False)
            .select_related(
                "district", "cluster", "village_score", "elevation"
            )
            .prefetch_related("characteristics")
            .annotate(destination_count=Count("destinations", distinct=True))
        )

        rec_lookup = cls._recommendation_lookup()

        features = []

        for village in villages:
            props = cls._village_properties(
                village,
                rec_lookup.get(village.id),
            )
            props["matched"] = True

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(village.longitude),
                        float(village.latitude),
                    ],
                },
                "properties": props,
            })

        return {
            "type": "FeatureCollection",
            "features": features,
            "status": {"count": len(features)},
        }

    # =========================================================
    # DESTINATION GEOJSON
    # =========================================================

    GEOJSON_CACHE_KEY = "gis:destination_geojson"
    GEOJSON_CACHE_TIMEOUT = 300

    @classmethod
    def destination_geojson(cls):
        """GeoJSON destinasi (di-cache; invalidasi otomatis saat staff edit)."""
        data = cache.get(cls.GEOJSON_CACHE_KEY)
        if data is not None:
            return data
        data = cls._build_destination_geojson()
        cache.set(cls.GEOJSON_CACHE_KEY, data, cls.GEOJSON_CACHE_TIMEOUT)
        return data

    @classmethod
    def invalidate_geojson_cache(cls):
        cache.delete(cls.GEOJSON_CACHE_KEY)

    @classmethod
    def _build_destination_geojson(cls):
        destinations = list(
            TouristDestination.objects
            .filter(is_active=True, latitude__isnull=False, longitude__isnull=False)
            .select_related("village", "district", "village__district")
            .prefetch_related(
                "categories",
                "cuisine_types",
                "wahanas",
                "bundles",
                "bundles__wahanas",
                "parking_fees",
            )
        )

        features = []

        for dest in destinations:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(dest.longitude),
                        float(dest.latitude),
                    ],
                },
                "properties": {
                    "id": dest.id,
                    "name": dest.name,
                    "village_id": dest.village_id,
                    "village_name": dest.village.name if dest.village else None,
                    "district_name": (
                        dest.effective_district.name
                        if dest.effective_district
                        else None
                    ),
                    "tourism_type": dest.tourism_type or "",
                    "place_type": dest.place_type,
                    "categories": [
                        category.name for category in dest.categories.all()
                    ],
                    "cuisine_types": [
                        c.name for c in dest.cuisine_types.all()
                    ],
                    "price_range_display": dest.price_range_display,
                    "ambiance": dest.ambiance or "",
                    "description": dest.description or "",
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
                    "ticket_price_weekday": dest.ticket_price_weekday_int,
                    "ticket_price_weekend": dest.ticket_price_weekend_int,
                    "parking_cost": dest.parking_cost_int,
                    "is_free": dest.is_free,
                    "ticket_type": dest.ticket_type,
                    "price_display": dest.price_display,
                    "parking_display": dest.parking_display,
                    "parking_fees_display": dest.parking_fees_display,
                    "is_free_parking": dest.is_free_parking,
                    "ride_prices_display": dest.ride_prices_display,
                    "bundle_prices_display": dest.bundle_prices_display,
                    "operating_hours_display": dest.operating_hours_display,
                    "is_open_24_hours": dest.is_open_24_hours,
                    "status": dest.status,
                    "status_label": dest.status_label,
                    "status_reason": dest.status_reason or "",
                    "google_maps_url": dest.google_maps_url(),
                    "google_maps_query": dest.effective_google_maps_query,
                    "elevation_meters": dest.elevation_meters,
                    "elevation_source": dest.elevation_source or "",
                    "temperature_c": dest.temperature_c,
                    "temperature_source": dest.temperature_source or "",
                    "temperature_date": (
                        dest.temperature_date.isoformat()
                        if dest.temperature_date
                        else None
                    ),
                    "difficulty": dest.difficulty or "",
                    "family_friendly": dest.family_friendly,
                    "elderly_friendly": dest.elderly_friendly,
                    "child_friendly": dest.child_friendly,
                    "indoor_outdoor": dest.indoor_outdoor or "",
                },
            })

        return {
            "type": "FeatureCollection",
            "features": features,
            "status": {
                "count": len(features),
            },
        }

    # =========================================================
    # LEGEND + STATUS
    # =========================================================

    @classmethod
    def legend(cls):
        return {
            "clusters": cls.cluster_legend(),
            "elevation_classes": cls.elevation_classes(),
            "characteristics": cls.characteristic_options(),
            "palette": list(settings.GIS_CLUSTER_PALETTE),
        }

    @classmethod
    def data_status(cls):
        features, _ = cls.load_features()
        return {
            "has_geojson": len(features) > 0,
            "n_geojson_features": len(features),
            "n_villages_with_coords": Village.objects.filter(
                latitude__isnull=False,
                longitude__isnull=False,
            ).count(),
            "n_destinations": TouristDestination.objects.filter(
                is_active=True,
                latitude__isnull=False,
                longitude__isnull=False,
            ).count(),
            "n_elevation": RegionElevation.objects.count(),
            "n_characteristics": RegionCharacteristic.objects.count(),
        }
