# GIS & Trip Planner (apps.gis)

Modul baru `apps.gis` menambahkan lapisan **geografis** dan **pariwisata** di
atas data penelitian yang sudah ada (Village/Cluster/TOPSIS), tanpa mengubah
atau menduplikasi fitur existing.

## Alur data

```
DATA DESA (master_village)
        ↓
DATABASE WILAYAH (gis_region_characteristic, gis_region_elevation)
        ↓
GEOJSON (static/geo/batas_desa_kota_batu.geojson) + enrichment DB
        ↓
GIS MAP (Leaflet) — layer batas / clustering / elevasi / karakteristik / destinasi
        ↓
PRUDENCE (tool-calling) → TRIP PLANNER → rekomendasi + itinerary + estimasi biaya
```

## Model

| Model | Tabel | Peran |
|---|---|---|
| `RegionCharacteristic` | `gis_region_characteristic` | karakteristik/keunikan desa (key-value bertipe, fleksibel) |
| `RegionElevation` | `gis_region_elevation` | statistik elevasi per desa (min/max/mean/median/std) |
| `TourismCategory` | `gis_tourism_category` | kategori wisata (dikelola admin, bukan hard-code) |
| `TouristDestination` | `gis_tourist_destination` | destinasi wisata (harga/jam/hari-tutup/aksesibilitas nullable) |

`Village.description` ditambahkan (nullable) untuk deskripsi singkat desa.

## Service

- `services/geo_service.py` — `GeoJSONService` membaca file batas wilayah lalu
  me-merge data DB (cluster, elevasi, karakteristik, skor, jumlah destinasi) ke
  `properties` tiap feature. Legend cluster dihitung dinamis (warna dari palet
  CVD-safe di `settings.GIS_CLUSTER_PALETTE`, bisa dioverride admin di
  `Cluster.color`). Kunci link: `village_id` → fallback `village_code` →
  `village_name`.
- `services/trip_planning.py` — `TripPlanningService` (filter → scoring
  transparan → itinerary → estimasi biaya). Bobot scoring di
  `settings.GIS_TRIP_SCORING_WEIGHTS`.
- `services/distance.py` — haversine (garis lurus), diisolasi agar mudah
  diganti routing API nanti.

## Endpoint

| URL | Nama | Fungsi |
|---|---|---|
| `/gis/` | `gis:map` | halaman peta (Leaflet) |
| `/gis/api/villages/geojson/` | `gis:api-villages-geojson` | GeoJSON desa ter-enrich (dari file batas) |
| `/gis/api/villages/points/geojson/` | `gis:api-villages-points-geojson` | titik pusat desa (fallback bila tanpa polygon) |
| `/gis/api/destinations/geojson/` | `gis:api-destinations-geojson` | GeoJSON titik destinasi |
| `/gis/api/legend/` | `gis:api-legend` | legend cluster + kelas elevasi + opsi karakteristik |

## Data koordinat desa

Koordinat titik pusat 21 desa diisi lewat management command
`import_village_coordinates` (sumber: node `place=village` OpenStreetMap).
3 desa tidak ditemukan di OSM (`Ngaglik`, `Sisir`, `Sumberbrantas`) — biarkan
null sampai ada sumber resmi. Batas poligon desa **tidak tersedia** di
OpenStreetMap; sumber resminya adalah Bappelitbangda / BIG.

## Data destinasi wisata (scraping OSM)

Destinasi wisata diisi lewat management command
`import_tourist_destinations` (sumber: OpenStreetMap Overpass API, ODbL).
Command menarik POI bertag wisata di bounding box Kota Batu (dihitung dari
koordinat 24 desa + padding), memetakan tag OSM ke `tourism_type` + kategori,
mencocokkan desa terdekat (haversine), dan menggali **hari tutup** dari tag
`opening_hours`. Idempotent (get-or-create per nama).

`TouristDestination.closed_days` adalah JSONField **fleksibel**:
`None` = belum diketahui, `[]` = buka setiap hari, `[5,6]` = tutup Sabtu+Minggu
(indeks mengikuti `date.weekday()`: 0=Senin … 6=Minggu). Trip planner memakai
`is_open_on(date)` supaya destinasi yang tutup di hari tertentu tidak
dijadwalkan. Catatan jujur: OSM hampir tidak punya data `opening_hours`/harga
untuk destinasi Indonesia, jadi mayoritas `closed_days` & harga tiket akan
`None` ("belum diketahui"/"belum tersedia") sampai diisi manual lewat form
(checkbox Hari Tutup).

## Chatbot (PRUDENCE)

Tool baru di `apps/chatbot/tools/village_tools.py`:
`get_village_characteristics`, `get_spatial_information`,
`get_clustering_results`, `search_destinations`, `get_destination_details`,
`build_itinerary`, `estimate_trip_budget`. Semua membaca database; tidak ada
data yang dikarang. `SYSTEM_PROMPT` diperluas dengan peran trip planner & GIS.

## Aturan penting

- **Tidak ada data palsu.** GeoJSON, koordinat, elevasi, harga, dan jam buka
  hanya bersumber dari database/file resmi. Yang belum ada dinyatakan
  "belum tersedia".
- **Layer tidak hard-code.** Warna cluster & kelas elevasi dihitung dinamis.
- **Query efisien.** `select_related` / `prefetch_related` / `annotate(Count)`
  dipakai untuk menghindari N+1; filtering dilakukan di database.
- **Akses.** Peta & endpoint GIS memakai `@login_required` (visitor boleh
  lihat); pengelolaan data lewat Django admin (staff/superuser).
