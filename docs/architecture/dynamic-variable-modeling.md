# Dynamic Variable Modeling

TRIP mendukung konfigurasi variable penelitian secara **dinamis** — jumlah,
urutan, peran, dan layer mediator tidak lagi di-hard-code di source code.

## Arsitektur

```
Database (master_variable + master_mediator_layer)
        ↓
Variable Configuration (role, order, mediator_layer)
        ↓
Indicator (FK → Variable, code mengikuti variable)
        ↓
Questionnaire (FK → Indicator)
        ↓
Response data
        ↓
Data mapping (decision matrix)
        ↓
Analysis (TOPSIS, K-Means, Feature Importance)
        ↓
Dashboard
```

**Single source of truth** = tabel `master_variable` + `master_mediator_layer`.
Indicator UI, Questionnaire, Data mapping, Analysis, dan Dashboard semuanya
membaca dari sini via `VariableConfigurationService`.

## Variable naming

| Role | Display code | Contoh |
|------|--------------|--------|
| Predictor | `X1 … Xn` | X1 Infrastruktur |
| Mediator  | `Y1 … Yn` | Y1 Kualitas Layanan |
| Response  | `Z1 … Zn` | Z1 Keberlanjutan |

`X1/Y1/Z1` adalah **display/analysis code** (di-generate otomatis dari
role + urutan), **bukan** primary key. Primary key = `id` (stabil, tidak
berubah saat reorder/move). Code di-regenerate oleh
`VariableConfigurationService.regenerate_codes()`.

## Mediator layers (0..N)

Mediator bisa punya 0 sampai N layer. `MediatorLayer` adalah model
tersendiri dengan `number` (unik) dan `is_active`.

```
0 layer : X → Z
1 layer : X → Y(layer 1) → Z
N layer : X → Y(1) → Y(2) → … → Y(N) → Z
```

- Layer yang `is_active=False` di-exclude dari analysis (Predictor → Response).
- Tidak ada batas jumlah layer; berasal dari database.

## Permission

| Role | Baca config | Mutasi (reorder/move/layer) |
|------|-------------|------------------------------|
| Visitor (login, non-staff) | ✅ | ❌ (403) |
| Staff | ✅ | ✅ |
| Superuser | ✅ | ✅ |

Authorisasi ditegakkan di **backend** (`_StaffRequiredJsonMixin`), bukan
cuma disembunyikan di frontend.

## Endpoints API

| Method | URL | Akses |
|--------|-----|-------|
| GET | `/master/variables/config/` | login |
| POST | `/master/variables/reorder/` | staff |
| POST | `/master/variables/move/` | staff |
| POST | `/master/mediator-layers/add/` | staff |
| POST | `/master/mediator-layers/<id>/deactivate/` | staff |
| POST | `/master/mediator-layers/<id>/activate/` | staff |
| POST | `/master/mediator-layers/<id>/remove/` | staff |

## Developer instructions

### Migration

```bash
python manage.py migrate master
```

### Test

```bash
python manage.py test apps.master
```

### Cara kerja kode ter-generate

`regenerate_codes()` mengurutkan variable aktif (role → layer → order),
lalu menetapkan `X{n}` untuk predictor, `Y{n}` global untuk mediator
(flatten semua layer), dan `Z{n}` untuk response. Code indicator mengikuti
prefix variable-nya (`Z1.1`, `Z1.2`, …).

### Cara membuat variable

Lewat halaman **Variable → Configure Variables** (drag-and-drop) atau
**Variable List → Add Variable**. `code` tidak perlu diinput manual —
diisi otomatis.

### Cara reorder / move / add layer

1. Buka `master/variables/configure/` (halaman "Configure Variables").
2. Drag kartu variable untuk reorder (dalam grup) atau pindah antar grup.
3. Klik "Add Mediator Layer" untuk menambah layer kosong.
4. Perubahan langsung tersimpan ke database.

### Cara disable mediator

Nonaktifkan layer mediator (tombol "Nonaktifkan" pada layer) — semua
indicator mediator di layer tersebut otomatis ter-exclude, dan analysis
berjalan sebagai Predictor → Response. Aktifkan kembali untuk memulihkan.

### Bagaimana analysis configuration di-generate

`VariableConfigurationService.load()` menghasilkan:

```python
{
    "predictors": [...],
    "mediator_layers": [[...], [...]],
    "responses": [...],
}
```

`active_indicators()` memfilter indicator yang aktif, variable aktif, dan
(untuk mediator) layer aktif. Feature matrix analysis dibangun dari sini,
sehingga analysis selalu konsisten dengan UI.

## Analisis relasi (predictor → response)

`RelationshipAnalysisService.run()` menghitung korelasi Pearson antara
skor tiap predictor dan tiap response (dari `VariableScore` antar desa).
Config-driven — daftar predictor/response diambil dari
`VariableConfigurationService.load()`, jadi otomatis mengikuti konfigurasi.
Tampil di ML dashboard (`/analytics/ml/`) dan endpoint
`/analytics/ml/relationship/`.

## Audit log

Perubahan konfigurasi variable dicatat di `VariableConfigAuditLog`
(model `master_variable_config_audit`): `user`, `action`
(reorder/move/add_layer/remove_layer/deactivate_layer/activate_layer),
`variable`, `old_role/new_role`, `old_order/new_order`,
`old_layer/new_layer`, `detail`, dan `created_at`. Setiap mutasi lewat
service mencatat entry (field `user` nullable untuk aksi programmatik).
