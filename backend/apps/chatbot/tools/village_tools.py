"""
Tool-tool yang boleh dipanggil chatbot publik.

ATURAN KETAT:
- Semua fungsi di sini HANYA membaca data AGREGAT per desa
  (cluster, skor rekomendasi, indikator dominan).
- TIDAK ADA fungsi yang mengakses data pribadi responden
  (nama, NIK, jawaban individu). Kalau perlu data baru,
  tambahkan lewat service yang sudah ada, JANGAN query
  langsung ke model Respondent/Response di sini.
"""

from django.db.models import Count

from apps.analytics.models import MLModelRegistry
from apps.analytics.services.feature_importance_service import (
    FeatureImportanceService,
)
from apps.analytics.services.ml_dashboard_service import (
    MLDashboardService,
)
from apps.gis.models import TouristDestination
from apps.gis.services.geo_service import GeoJSONService
from apps.gis.services.trip_planning import TripPlanningService
from apps.master.models import Village
from apps.recommendation.services.recommendation_service import (
    RecommendationService,
)


def list_villages(**kwargs):

    names = list(
        Village.objects.values_list("name", flat=True).order_by("name")
    )

    return {
        "total": len(names),
        "villages": names,
    }


def get_village_info(village_name, **kwargs):

    village = (
        Village.objects
        .filter(name__iexact=village_name.strip())
        .select_related("cluster")
        .first()
    )

    if village is None:

        return {
            "found": False,
            "message": (
                f"Desa \"{village_name}\" tidak ditemukan di sistem."
            ),
        }

    ranking = RecommendationService.dashboard().get("ranking", [])

    # FIXED: ranking sekarang berupa list of dict hasil cache
    # (village_id, village_name, ...) -- BUKAN objek Django lagi.
    match = next(
        (
            item
            for item in ranking
            if item["village_id"] == village.id
        ),
        None,
    )

    return {

        "found": True,

        "village": village.name,

        "cluster": (
            village.cluster.name if village.cluster else "Belum dianalisis"
        ),

        "status": match["status"] if match else "Belum ada data",

        "recommendation": (
            match["recommendation"] if match else None
        ),

        "rank": (
            ranking.index(match) + 1 if match else None
        ),

        "total_village_ranked": len(ranking),

    }


def get_top_villages(limit=5, **kwargs):

    ranking = RecommendationService.dashboard().get("ranking", [])

    limit = max(1, min(int(limit or 5), 24))

    top = ranking[:limit]

    return {

        "villages": [

            {

                "rank": index + 1,

                # FIXED: village_name langsung (dict), bukan
                # item["village"].name (objek).
                "village": item["village_name"],

                "status": item["status"],

                "recommendation": item["recommendation"],

            }

            for index, item in enumerate(top)

        ],

    }


def get_dominant_factors(**kwargs):

    variables = FeatureImportanceService.dominant_variables()

    return {

        "factors": [

            {

                "name": item["name"],

                "percentage": item["percentage"],

            }

            for item in variables[:5]

        ],

    }


def get_general_summary(**kwargs):

    variable_importance = FeatureImportanceService.dominant_variables()

    summary = MLDashboardService.summary()

    narrative = MLDashboardService.narrative_summary(
        variable_importance,
    )

    return {

        "total_village": summary["total_village"],

        "n_clusters": summary["n_clusters"],

        "narrative": narrative,

    }


# =========================================================
# GIS & TRIP PLANNER TOOLS (integrasi data spasial + pariwisata)
# =========================================================

def get_village_characteristics(village_name, **kwargs):

    village = (
        Village.objects
        .filter(name__iexact=village_name.strip())
        .prefetch_related("characteristics")
        .first()
    )

    if village is None:

        return {
            "found": False,
            "message": f"Desa \"{village_name}\" tidak ditemukan di sistem.",
        }

    characteristics = [
        {
            "type": c.characteristic_type,
            "name": c.characteristic_name,
            "value": c.value,
            "source": c.source or "",
        }
        for c in village.characteristics.all()
    ]

    return {
        "found": True,
        "village": village.name,
        "description": village.description or "",
        "characteristics": characteristics,
    }


def get_spatial_information(village_name, **kwargs):

    village = (
        Village.objects
        .select_related("district", "cluster", "village_score", "elevation")
        .prefetch_related("characteristics")
        .annotate(destination_count=Count("destinations", distinct=True))
        .filter(name__iexact=village_name.strip())
        .first()
    )

    if village is None:

        return {
            "found": False,
            "message": f"Desa \"{village_name}\" tidak ditemukan di sistem.",
        }

    props = GeoJSONService._village_properties(village)
    props["found"] = True

    return props


def get_clustering_results(**kwargs):

    registry = MLModelRegistry.objects.filter(is_active=True).first()

    if registry is None:

        return {
            "found": False,
            "message": "Hasil clustering belum tersedia.",
        }

    clusters = GeoJSONService.cluster_legend()

    villages = list(
        Village.objects
        .filter(cluster__isnull=False)
        .select_related("cluster")
        .values("name", "cluster__name", "cluster__code")
        .order_by("name")
    )

    return {
        "found": True,
        "n_clusters": registry.n_clusters,
        "silhouette_score": registry.silhouette_score,
        "clusters": clusters,
        "villages": [
            {
                "village": item["name"],
                "cluster": item["cluster__name"],
                "cluster_code": item["cluster__code"],
            }
            for item in villages
        ],
    }


def search_destinations(**kwargs):
    """
    Cari & ranking destinasi wisata berdasarkan parameter trip user.
    Semua argumen opsional; nilai kosong dianggap "tidak dibatasi".
    """
    return TripPlanningService.search_destinations(kwargs)


def get_destination_details(destination_id=None, name=None, **kwargs):

    return TripPlanningService.get_destination_details(
        destination_id=destination_id,
        name=name,
    )


def build_itinerary(destination_ids=None, **kwargs):
    """
    Susun itinerary berdasarkan durasi, transportasi, dan destinasi.
    """
    return TripPlanningService.build_itinerary(kwargs, destination_ids=destination_ids)


def estimate_trip_budget(destination_ids=None, **kwargs):
    """
    Estimasi biaya trip berdasarkan data harga yang tersedia di database.
    """
    return TripPlanningService.estimate_budget(kwargs, destination_ids=destination_ids)


def get_restaurants(flavor=None, max_price=None, village=None, **kwargs):
    """
    Cari restaurant / tempat makan berdasarkan cita rasa, budget, lokasi.
    """
    qs = (
        TouristDestination.objects
        .filter(place_type="restaurant", is_active=True)
        .select_related("village", "district", "village__district")
        .prefetch_related("cuisine_types")
    )

    if flavor:
        qs = qs.filter(cuisine_types__name__icontains=flavor).distinct()

    if village:
        qs = qs.filter(village__name__icontains=village)

    results = []
    for r in qs.order_by("name")[:20]:
        if (
            max_price is not None
            and r.price_min is not None
            and r.price_min > max_price
        ):
            continue
        results.append({
            "id": r.id,
            "name": r.name,
            "village": r.village.name if r.village else None,
            "price_range": r.price_range_display,
            "cuisine_types": [c.name for c in r.cuisine_types.all()],
            "ambiance": r.ambiance or "",
            "google_maps_url": r.google_maps_url(),
        })

    return {"count": len(results), "results": results}


TOOL_REGISTRY = {

    "list_villages": list_villages,

    "get_village_info": get_village_info,

    "get_top_villages": get_top_villages,

    "get_dominant_factors": get_dominant_factors,

    "get_general_summary": get_general_summary,

    "get_village_characteristics": get_village_characteristics,

    "get_spatial_information": get_spatial_information,

    "get_clustering_results": get_clustering_results,

    "search_destinations": search_destinations,

    "get_destination_details": get_destination_details,

    "build_itinerary": build_itinerary,

    "estimate_trip_budget": estimate_trip_budget,

    "get_restaurants": get_restaurants,

}


TOOLS_SCHEMA = [

    {
        "name": "list_villages",
        "description": (
            "Ambil daftar semua nama desa wisata yang ada di sistem."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },

    {
        "name": "get_village_info",
        "description": (
            "Ambil status dan rekomendasi untuk SATU desa wisata "
            "tertentu berdasarkan namanya."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "village_name": {
                    "type": "string",
                    "description": (
                        "Nama desa, contoh: 'Punten' atau 'Tlekung'."
                    ),
                },
            },
            "required": ["village_name"],
        },
    },

    {
        "name": "get_top_villages",
        "description": (
            "Ambil daftar desa wisata dengan peringkat/prioritas "
            "rekomendasi tertinggi."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": (
                        "Jumlah desa yang ingin ditampilkan "
                        "(default 5, maksimal 24)."
                    ),
                },
            },
        },
    },

    {
        "name": "get_dominant_factors",
        "description": (
            "Ambil faktor/indikator yang paling berpengaruh terhadap "
            "karakteristik desa wisata secara umum."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },

    {
        "name": "get_general_summary",
        "description": (
            "Ambil ringkasan umum kondisi seluruh desa wisata "
            "Kota Batu (jumlah desa, jumlah kelompok, kesimpulan)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },

    {
        "name": "get_village_characteristics",
        "description": (
            "Ambil karakteristik/keunikan SATU desa (komoditas, "
            "potensi wisata, geografis, budaya, fasilitas, dll)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "village_name": {
                    "type": "string",
                    "description": "Nama desa, contoh: 'Punten'.",
                },
            },
            "required": ["village_name"],
        },
    },

    {
        "name": "get_spatial_information",
        "description": (
            "Ambil informasi spasial SATU desa: elevasi, koordinat, "
            "cluster, jumlah destinasi, dan karakteristik wilayah."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "village_name": {
                    "type": "string",
                    "description": "Nama desa, contoh: 'Punten'.",
                },
            },
            "required": ["village_name"],
        },
    },

    {
        "name": "get_clustering_results",
        "description": (
            "Ambil hasil clustering desa wisata: jumlah cluster, "
            "silhouette score, dan pemetaan desa ke cluster-nya."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },

    {
        "name": "search_destinations",
        "description": (
            "Cari dan urutkan destinasi wisata yang cocok dengan "
            "kebutuhan trip user (preferensi, budget, durasi, "
            "aksesibilitas, lansia/anak). Hasil sudah diberi skor."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "duration_days": {
                    "type": "integer",
                    "description": "Lama liburan dalam hari.",
                },
                "start_date": {
                    "type": "string",
                    "description": (
                        "Tanggal mulai perjalanan (format YYYY-MM-DD), "
                        "dipakai untuk membedakan harga weekday vs weekend."
                    ),
                },
                "budget": {
                    "type": "number",
                    "description": "Anggaran dalam Rupiah.",
                },
                "budget_scope": {
                    "type": "string",
                    "enum": ["total", "per_person"],
                    "description": (
                        "'total' jika budget untuk seluruh perjalanan, "
                        "'per_person' jika per orang."
                    ),
                },
                "transportation": {
                    "type": "string",
                    "enum": ["motorcycle", "car", "walking", "public"],
                    "description": "Moda transportasi.",
                },
                "traveler_count": {
                    "type": "integer",
                    "description": "Jumlah orang yang ikut.",
                },
                "elderly": {
                    "type": "boolean",
                    "description": "True jika ada lansia.",
                },
                "children": {
                    "type": "boolean",
                    "description": "True jika ada anak kecil.",
                },
                "preferences": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Preferensi jenis wisata, mis. ['nature', "
                        "'air terjun', 'perkebunan']."
                    ),
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Kategori wisata eksplisit dari database.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Jumlah hasil maksimal (default 10).",
                },
            },
        },
    },

    {
        "name": "get_destination_details",
        "description": (
            "Ambil detail lengkap SATU destinasi wisata: harga tiket "
            "masuk (HTM), daftar wahana tambahan (dengan kategori harga: "
            "termasuk HTM / berbayar / termasuk paket / harga belum "
            "tersedia), tiket bundle (beserta isi & status termasuk HTM), "
            "biaya parkir per jenis kendaraan, jam buka, fasilitas, dan "
            "aksesibilitas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "destination_id": {
                    "type": "integer",
                    "description": "ID destinasi dari database.",
                },
                "name": {
                    "type": "string",
                    "description": "Nama destinasi.",
                },
            },
        },
    },

    {
        "name": "build_itinerary",
        "description": (
            "Susun jadwal itinerary harian berdasarkan durasi, "
            "transportasi, jam buka, dan durasi kunjungan destinasi."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "duration_days": {
                    "type": "integer",
                    "description": "Lama liburan dalam hari.",
                },
                "start_date": {
                    "type": "string",
                    "description": "Tanggal mulai perjalanan (YYYY-MM-DD).",
                },
                "transportation": {
                    "type": "string",
                    "enum": ["motorcycle", "car", "walking", "public"],
                },
                "destination_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": (
                        "Opsional: id destinasi terpilih. Kalau kosong, "
                        "sistem mencari sendiri."
                    ),
                },
                "preferences": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "elderly": {"type": "boolean"},
                "children": {"type": "boolean"},
                "budget": {"type": "number"},
                "traveler_count": {"type": "integer"},
                "vehicles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": (
                                    "Jenis kendaraan, mis. 'motor' atau 'mobil'."
                                ),
                            },
                            "count": {
                                "type": "integer",
                                "description": "Jumlah kendaraan jenis itu.",
                            },
                        },
                    },
                    "description": (
                        "Konfigurasi kendaraan (opsional). Contoh: "
                        "[{'type': 'motor', 'count': 4}] untuk 4 motor."
                    ),
                },
            },
        },
    },

    {
        "name": "estimate_trip_budget",
        "description": (
            "Estimasi biaya trip berdasarkan harga tiket/parkir yang "
            "tersedia di database. Biaya yang belum ada dinyatakan "
            "'belum tersedia', tidak dikarang."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "destination_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Opsional: id destinasi terpilih.",
                },
                "start_date": {
                    "type": "string",
                    "description": (
                        "Tanggal mulai (YYYY-MM-DD) untuk memilih harga "
                        "weekday/weekend."
                    ),
                },
                "budget": {"type": "number"},
                "traveler_count": {"type": "integer"},
                "transportation": {
                    "type": "string",
                    "enum": ["motorcycle", "car", "walking", "public"],
                },
                "preferences": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "elderly": {"type": "boolean"},
                "children": {"type": "boolean"},
                "vehicles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": (
                                    "Jenis kendaraan, mis. 'motor' atau 'mobil'."
                                ),
                            },
                            "count": {
                                "type": "integer",
                                "description": "Jumlah kendaraan jenis itu.",
                            },
                        },
                    },
                    "description": (
                        "Konfigurasi kendaraan (opsional) untuk menghitung "
                        "biaya parkir per jenis kendaraan."
                    ),
                },
            },
        },
    },

    {
        "name": "get_restaurants",
        "description": (
            "Cari restaurant / tempat makan di Kota Batu berdasarkan cita "
            "rasa (pedas/manis/gurih/...), jenis masakan, budget (max_price), "
            "atau lokasi desa. Restaurant memakai range harga, BUKAN HTM."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "flavor": {
                    "type": "string",
                    "description": (
                        "Cita rasa / jenis masakan, mis. 'pedas', 'manis', "
                        "'nusantara', 'western'."
                    ),
                },
                "max_price": {
                    "type": "number",
                    "description": "Batas atas harga makanan per orang (IDR).",
                },
                "village": {
                    "type": "string",
                    "description": "Nama desa/kecamatan lokasi.",
                },
            },
        },
    },

]


# Tool yang HANYA berhubungan wisata (boleh dipakai visitor publik).
# Tool riset internal (clustering, ranking desa, indikator, dsb.) hanya
# boleh dipakai staff/superuser.
TOURISM_TOOL_NAMES = {
    "search_destinations",
    "get_destination_details",
    "get_restaurants",
    "build_itinerary",
    "estimate_trip_budget",
}


def tools_schema_for(is_staff):
    """
    Daftar tool yang boleh dipakai user. Visitor (bukan staff) hanya dapat
    tool wisata; staff/superuser dapat seluruh tool (termasuk riset internal).
    """
    if is_staff:
        return TOOLS_SCHEMA
    return [tool for tool in TOOLS_SCHEMA if tool["name"] in TOURISM_TOOL_NAMES]


def to_openai_tools_schema(tools=None):
    """
    DeepSeek pakai format tool-calling ala OpenAI (beda struktur
    dari Anthropic), jadi TOOLS_SCHEMA di atas perlu dikonversi.
    """
    tools = tools if tools is not None else TOOLS_SCHEMA

    return [

        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }

        for tool in tools

    ]


def execute_tool(name, tool_input):

    handler = TOOL_REGISTRY.get(name)

    if handler is None:

        return {"error": f"Tool \"{name}\" tidak dikenali."}

    try:

        return handler(**(tool_input or {}))

    except Exception as error:

        return {"error": str(error)}