# Data GeoJSON Batas Wilayah Kota Batu

Folder ini menyimpan data batas wilayah resmi untuk peta "Peta Analisis Desa
Wisata". **File `batas_desa_kota_batu.geojson` saat ini sengaja KOSONG** —
sistem tidak membuat polygon palsu dan tidak mengarang koordinat.

## Cara mengisi

Letakkan file GeoJSON **resmi** (mis. dari Bappelitbangda Kota Batu, BIG, atau
sumber pemerintah yang sah) ke `backend/static/geo/batas_desa_kota_batu.geojson`,
lalu pastikan tiap feature polygon desa memiliki `properties` minimal:

```json
{
  "type": "Feature",
  "geometry": { "type": "Polygon", "coordinates": [ [ [lon, lat], ... ] ] },
  "properties": {
    "village_id": 19,
    "village_name": "Beji",
    "district_id": 7,
    "district_name": "Junrejo"
  }
}
```

## Aturan penghubung (link) ke database

Sistem menghubungkan polygon ke data database (`master_village`) dengan
prioritas berikut — gunakan ID database bila tersedia, jangan hanya nama:

1. `village_id`  → `Village.id` (primary key, paling disarankan)
2. `village_code` → `Village.code`
3. `village_name` → `Village.name` (fallback terakhir, case-insensitive)

`district_id` / `district_name` dipakai untuk identitas kecamatan dan layer
"Batas Kecamatan" (bila tersedia file terpisah nanti).

## Layer tambahan (opsional)

Untuk layer "Batas Kota Batu" dan "Batas Kecamatan" yang lebih detail,
tambahkan file GeoJSON terpisah dengan pola penamaan yang sama, misalnya
`batas_kecamatan_kota_batu.geojson` — struktur layer dirancang agar bisa
ditambah tanpa mengubah kode inti.
