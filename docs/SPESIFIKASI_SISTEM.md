# Spesifikasi Sistem TRIP

**Tourism Resource Integration Platform — Sistem Pendukung Keputusan (DSS) Desa Wisata**

> Dokumen ini menjelaskan cara kerja dan spesifikasi seluruh sistem TRIP, ditulis agar bisa dibaca manusia maupun AI (untuk keperluan penulisan skripsi). Istilah teknis disimpan dalam Bahasa Inggris, penjelasan dalam Bahasa Indonesia.

---

## 1. Ringkasan Sistem

TRIP adalah **sistem pendukung keputusan berbasis web** untuk mendukung pengambilan keputusan berbasis data dalam pengembangan desa wisata di **Kota Batu**, dikembangkan bersama **Bappelitbangda Kota Batu**.

Sistem mengintegrasikan tiga fungsi utama:

1. **Manajemen data penelitian** — data desa wisata, variabel, indikator, kuesioner, responden, dan jawaban survei.
2. **Analisis statistik & machine learning** — clustering desa, analisis jalur (SEM), Latent Class Analysis, feature importance, dan interpretabilitas (SHAP).
3. **Sistem pendukung keputusan** — perankingan desa (TOPSIS), rekomendasi pengembangan, dan dashboard interaktif.

**Skala data saat ini** (dari README):

| Entitas | Jumlah |
|---|---|
| Desa wisata | 24 |
| Responden | 1.152 |
| Variabel (konstruk) | 11 |
| Indikator (item Likert) | 88 |

---

## 2. Teknologi

### Backend
- **Python 3.13**, **Django 5.2**
- Database: **PostgreSQL** (produksi) / **SQLite** (pengembangan)
- Web server: **Gunicorn** + **WhiteNoise** (static), dideploy dengan **Docker** (Railway)

### Frontend
- **Bootstrap 5** (UI), **vanilla JavaScript**
- Charting: **Chart.js**, **Plotly**, **Leaflet** (peta)

### Data Science & ML
- **scikit-learn** (K-Means, PCA, Random Forest, StandardScaler)
- **numpy / pandas / joblib**
- **semopy** (CFA & SEM), **stepmix** (Latent Class Analysis)
- **xgboost** + **shap** (surrogate model + interpretabilitas)
- **statsmodels** (korelasi polychoric, alat statistik)

### AI / Chatbot
- **Anthropic API** (chatbot "PRUDENCE")

---

## 3. Arsitektur & Struktur Project

Django modular (satu app = satu domain). Struktur utama:

```text
backend/
├── config/            # settings.py, urls.py (routing utama), wsgi
├── common/            # model dasar (BaseModel), middleware, decorators (staff_required)
├── apps/
│   ├── dashboard/     # halaman beranda (landing / KPI staff)
│   ├── master/        # data master (district, village, cluster, variable, indicator, questionnaire)
│   ├── survey/        # manajemen survei
│   ├── respondent/    # manajemen responden
│   ├── response/      # jawaban responden (Likert) + skor agregat
│   ├── analytics/     # dashboard analitik, clustering, feature importance, warna cluster
│   ├── recommendation/# perankingan TOPSIS (DSS) + cache hasil
│   ├── chatbot/       # chatbot PRUDENCE
│   ├── gis/           # peta wisata, destinasi, itinerary
│   └── survey_analysis/ # pipeline analisis responden-level (Reliability → CFA → SEM → LCA → ML → SHAP)
├── templates/         # template global (base, sidebar, navbar)
├── static/            # CSS/JS statis
└── manage.py
```

### Routing utama (`config/urls.py`)

| Prefix URL | App | Fungsi |
|---|---|---|
| `/` | dashboard | Beranda (staff → KPI, visitor → jelajah) |
| `/master/` | master | Data master |
| `/survey/` | survey | Survei |
| `/respondent/` | respondent | Responden |
| `/response/` | response | Jawaban |
| `/analytics/` | analytics | Dashboard analitik + ML |
| `/recommendation/` | recommendation | Ranking TOPSIS |
| `/chatbot/` | chatbot | Chatbot |
| `/gis/` | gis | Peta wisata |
| `/survey-analysis/` | survey_analysis | UI status pipeline |

---

## 4. Model Data (Data Model)

### Data master (`apps.master`)

- **District** — kecamatan.
- **Village** — desa wisata (FK ke District dan Cluster).
- **Cluster** — label cluster desa hasil K-Means (`code`, `name`, `color`).
- **MediatorLayer** — layer variabel mediator (1..N).
- **Variable** — variabel penelitian. Punya `role` (**predictor** / **mediator** / **response**) dan `code` yang di-generate otomatis (`X1…Xn` / `Y1…Yn` / `Z1…Zn`). Primary key tetap `id` (stabil), `code` hanya display/analysis.
- **Indicator** — indikator (item) di bawah variabel (`code` seperti `X1.1`), punya `weight` dan `criterion_type` (`benefit`/`cost`).
- **Questionnaire** — item kuesioner Likert (FK ke Indicator).
- **VariableConfigAuditLog** — log perubahan konfigurasi variabel.

### Data penelitian
- **Respondent** — responden (FK ke Village).
- **Survey** — survei.
- **Response** — jawaban responden (`answer_integer` untuk Likert 1–5, `answer_boolean`, `answer_decimal`).

### Model hasil analisis
- **MLModelRegistry** (`apps.analytics`) — menyimpan hasil K-Means: jumlah cluster, mapping cluster, silhouette score, feature/variable importance, timestamp.
- **RecommendationResult** (`apps.recommendation`) — cache hasil ranking TOPSIS.
- **AnalysisState** — singleton penanda "signature konfigurasi" untuk deteksi data berubah (staleness).

---

## 5. Alur Analisis (Dua Pipeline)

Sistem punya **dua pipeline analisis** yang berbeda level:

### Pipeline A — Level Desa (clustering & rekomendasi)

Dijalankan lewat tombol **"Retrain Model"** di dashboard. Alurnya:

```text
Response (jawaban responden)
        ↓  ScoreAggregationService.populate_all()
Skor agregat per desa (VariableScore → VillageScore)
        ↓  AnalyticsSelector.feature_matrix()
Matriks [desa × indikator]
        ↓
┌───────────────────────────┐
│ 1. K-Means Clustering     │  (StandardScaler → KMeans k=3)
│ 2. Silhouette Score       │  (evaluasi kualitas cluster)
│ 3. Feature Importance     │  (Random Forest, target = label cluster)
│ 4. PCA (2D)               │  (visualisasi scatter)
└───────────────────────────┘
        ↓
ClusterRecommendationService.rank_within_clusters()
        ↓
TOPSIS per cluster (ranking desa di dalam cluster masing-masing)
        ↓
Dashboard (/analytics/ml/)
```

### Pipeline B — Level Responden (SEM / LCA / SHAP)

Dijalankan lewat tombol **"Run SEM/LCA/SHAP"** (atau `python manage.py run_survey_pipeline`), berjalan **di background** (subprocess) karena berat. Alurnya:

```text
Response Likert
        ↓  load_dataset() → pivot menjadi matriks [responden × item]
1. VALIDATION     → missing, variance, normality
2. RELIABILITY    → Cronbach's Alpha & McDonald's Omega per konstruk   (STOP jika < 0.60)
3. CFA (measurement) → model pengukuran, fit indices (CFI/TLI/RMSEA/SRMR)
4. SEM (structural)  → 24 jalur antar konstruk, koefisien jalur + efek
5. LCA           → Latent Class Analysis (2–6 kelas, pilih via BIC + entropy)
6. ML (surrogate) → XGBoost/Random Forest prediksi kelas LCA   (STOP jika akurasi < 0.80)
7. SHAP         → interpretabilitas (global + per kelas)
8. REPORT       → laporan markdown + file output CSV/JSON
```

**STOP conditions** (pipeline berhenti, tidak dipaksa lanjut):

| Tahap | Kondisi STOP |
|---|---|
| Reliability | Alpha ATAU Omega < 0.60 |
| CFA | CFI/TLI/RMSEA/SRMR gagal kriteria |
| ML | Akurasi surrogate < 0.80 |

Semua hasil ditulis ke `apps/survey_analysis/outputs/` (CSV/JSON) dan dibaca oleh dashboard.

---

## 6. Penjelasan Metode & Formula

### 6.1 K-Means Clustering (`apps.analytics.ml.clustering`)

Mengelompokkan desa wisata menjadi **k = 3 cluster** berdasarkan karakteristik indikatornya.

- **Preprocessing**: `StandardScaler` (z-score) agar tiap indikator setara skala.
- **Algoritme**: K-Means (`n_init=10`, `random_state=42`), meminimalkan **inertia** (sum of squared distances ke centroid).

$$J = \sum_{i=1}^{k} \sum_{x \in C_i} \lVert x - \mu_i \rVert^2$$

- **Evaluasi**: **Silhouette Score** untuk mengukur seberapa baik tiap desa masuk ke clusternya.

$$s(i) = \frac{b(i) - a(i)}{\max(a(i), b(i))}$$

di mana `a(i)` = jarak rata-rata ke anggota cluster sendiri, `b(i)` = jarak rata-rata ke cluster terdekat. Nilai −1 s.d. +1; semakin mendekati 1 semakin baik.

### 6.2 Feature Importance — Random Forest (`apps.analytics.ml.feature_importance`)

Melatih **Random Forest classifier** (300 pohon) dengan **target = label cluster K-Means** (bukan untuk prediksi produksi, tapi untuk menjawab: "indikator mana yang paling membedakan antar cluster?").

Importance dihitung dari **Gini importance / mean decrease impurity** tiap fitur, lalu diagregasi per variabel menjadi persentase (total 100%).

### 6.3 TOPSIS (`apps.recommendation.services.topsis`)

**Technique for Order Preference by Similarity to Ideal Solution** — meranking alternatif (desa) berdasarkan kedekatan ke solusi ideal.

Langkah (sesuai implementasi):

1. **Normalisasi vektor**:

$$r_{ij} = \frac{x_{ij}}{\sqrt{\sum_{i} x_{ij}^{2}}}$$

2. **Matriks berbobot**:

$$v_{ij} = w_j \cdot r_{ij}$$

3. **Solusi ideal positif/negatif** (`benefit` = max diinginkan, `cost` = min diinginkan):

$$A^+ = \{ \max_i v_{ij} \text{ jika benefit; } \min_i v_{ij} \text{ jika cost} \}$$

$$A^- = \{ \min_i v_{ij} \text{ jika benefit; } \max_i v_{ij} \text{ jika cost} \}$$

4. **Jarak separasi** (Euclidean):

$$S_i^+ = \sqrt{\sum_j (v_{ij} - v_j^+)^2}, \quad S_i^- = \sqrt{\sum_j (v_{ij} - v_j^-)^2}$$

5. **Kedekatan relatif (preference)**:

$$C_i = \frac{S_i^-}{S_i^+ + S_i^-}$$

Nilai `C_i` (0–1) dijadikan skor ranking. Di sistem ini TOPSIS dijalankan **per cluster** (ranking adil antar desa selevel), ditambah TOPSIS lintas desa di app `recommendation`.

### 6.4 PCA (Principal Component Analysis)

Reduksi dimensi ke 2 komponen untuk **visualisasi scatter** (bukan inferensi). Matriks [desa/responden × indikator] diproyeksikan ke 2 sumbu utama (eigenvector dengan eigenvalue terbesar).

### 6.5 Reliabilitas (`apps.survey_analysis.reliability`)

- **Cronbach's Alpha**:

$$\alpha = \frac{k}{k-1}\left(1 - \frac{\sum \sigma_i^2}{\sigma_{total}^2}\right)$$

- **McDonald's Omega** (model 1-faktor, loading terstandarisasi λ):

$$\omega = \frac{(\sum \lambda)^2}{(\sum \lambda)^2 + \sum (1 - \lambda^2)}$$

Interpretasi: ≥ 0.70 *acceptable*, 0.60–0.70 *questionable*, < 0.60 *problematic*. Pipeline STOP bila < 0.60.

### 6.6 CFA & SEM (`apps.survey_analysis.cfa`)

- **CFA (Confirmatory Factor Analysis)**: menguji model pengukuran (apakah item benar mengukur konstruk latennya).
- **SEM (Structural Equation Modeling)**: menguji hubungan antar konstruk laten.

Model punya **11 konstruk** (5 eksogen X, 3 mediator Y, 3 outcome Z) dan **24 jalur struktural** (15 X→Y + 9 Y→Z, full mediation tanpa jalur langsung X→Z).

**Estimator** (engine `semopy`, data ordinal Likert):

| Estimator | Keterangan |
|---|---|
| `ULS` | Unweighted Least Squares pada matriks **korelasi polychoric** (terbaik yang didukung semopy untuk ordinal) |
| `DWLS` | Diagonally Weighted Least Squares pada data mentah (Pearson) |
| `MLW` | Maximum Likelihood (kontinu, hanya perbandingan) |

**Objective ULS** (meminimalkan selisih matriks kovarian sampel `S` vs model-implied `Σ(θ)`):

$$F_{ULS} = \mathrm{tr}\big((S - \Sigma(\theta))^2\big)$$

**Fit indices** (kriteria Hu & Bentler 1999): **CFI ≥ 0.95, TLI ≥ 0.95, RMSEA ≤ 0.06, SRMR ≤ 0.08**, plus chi-square, AIC, BIC.

**Efek**: `compute_effects()` menghitung efek langsung, tidak langsung (X→Y→Z), dan total dari koefisien jalur.

> Catatan metodologis (ada di `semopy_model.py`): semopy 2.3.x tidak bisa melakukan **WLSMV sejati** (polychoric + DWLS). ULS pada polychoric adalah pendekatan valid namun bukan WLSMV; untuk WLSMV penuh tersedia engine `lavaan` (rpy2 + R).

### 6.7 Latent Class Analysis — LCA (`apps.survey_analysis.lca`)

Mengelompokkan **responden** ke kelas laten berdasarkan pola jawaban item Likert. Engine: **stepmix** (`measurement='categorical'`).

Model:

$$P(Y) = \sum_{c=1}^{C} \pi_c \prod_{j} P(Y_j \mid C = c)$$

- **Pemilihan jumlah kelas** (2–6): **BIC** sebagai kriteria utama, dikombinasikan dengan **entropy** (> 0.80), ukuran kelas minimum (> 5%), dan interpretabilitas.

$$BIC = -2 \ln L + k \ln(n), \quad AIC = -2 \ln L + 2k$$

- **Entropy relatif** mengukur keterpisahan kelas (seberapa "tegas" keanggotaan responden).
- **Average Posterior Probability (AvePP)** per kelas — kualitas klasifikasi per kelas.
- **Class profiles**: item dengan probabilitas persetujuan tertinggi per kelas.

### 6.8 Surrogate ML + SHAP (`apps.survey_analysis.ml` & `.shap`)

- Melatih **XGBoost** dan **Random Forest** untuk memprediksi **kelas LCA** dari item (train/test 80/20, 5-fold CV). Ini "surrogate model" — menjembatani kelas laten (yang tak bisa diukur langsung) dengan item yang bisa diamati.
- **STOP** bila akurasi < 0.80.
- **SHAP (SHapley Additive exPlanations)** via `TreeExplainer`: menghitung kontribusi tiap item terhadap prediksi kelas. Output:
  - **Global importance**: mean |SHAP| per item.
  - **Per-class importance**: mean |SHAP| per item per kelas.
  - **Arah dominan** (positif/negatif) dan **kelas paling terdampak** per item.

Nilai Shapley untuk fitur `j`:

$$\phi_j = \sum_{S \subseteq N \setminus \{j\}} \frac{|S|!(|N|-|S|-1)!}{|N|!} \left[ f(S \cup \{j\}) - f(S) \right]$$

---

## 7. Dashboard & Visualisasi

Halaman utama analisis: **`/analytics/ml/`** (`apps.analytics.templates.analytics.ml_dashboard.html`).

Menampilkan:

1. **KPI** — jumlah desa/responden/cluster, silhouette score (+ badge kualitas).
2. **Clustering desa** — pie distribusi cluster, scatter PCA, tabel desa + badge cluster.
3. **Feature importance** — bar chart kontribusi variabel.
4. **Relasi predictor → response** — tabel korelasi Pearson.
5. **Ranking TOPSIS per cluster** — tabel ranking desa di tiap cluster.
6. **Analisis Survei (SEM/LCA/SHAP)** — fit indices SEM, kelas LCA (tabel + legend + entropy badge), SHAP global.
7. **Evaluasi LCA** — chart BIC/AIC vs jumlah kelas.
8. **Sebaran responden per kelas** — scatter PCA berwarna kelas.
9. **Profil kelas** — bar chart item persetujuan tertinggi per kelas.
10. **Feature importance per kelas (SHAP)** — grouped bar.

Charting memakai **Chart.js** (server-rendered Django template + vanilla JS).

### Sistem Warna Cluster (`apps.analytics.colors.py`)

Warna cluster **terpusat** (single source of truth) memakai palet **Okabe-Ito** (colorblind-friendly):

```python
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
UNASSIGNED_COLOR = "#6c757d"  # gray (belum terklasifikasi)
```

- **K-Means**: warna dari `cluster_color_map()` (urut `code`, stabil) — cluster yang sama selalu warna yang sama.
- **LCA**: kelas `c` → `color_for_index(c)`.
- Warna dipakai konsisten di pie, scatter, tabel, badge, chart, dan legend.

---

## 8. Deployment

- **Docker** (`Dockerfile`): `python:3.13-slim`, install dependensi, `collectstatic`, lalu jalankan migrasi + **Gunicorn** (`--timeout 600`).
- Pipeline berat (SEM/LCA) berjalan sebagai **subprocess background** (detached), tidak memblokir request web.

---

## 9. Ringkasan Mapping "Kode → Metode"

| Kode | Metode | Fungsi |
|---|---|---|
| `analytics/ml/clustering.py` | K-Means + Silhouette | Cluster desa |
| `analytics/ml/feature_importance.py` | Random Forest | Importance indikator |
| `recommendation/services/topsis.py` | TOPSIS | Ranking desa |
| `analytics/services/cluster_recommendation_service.py` | TOPSIS per cluster | Ranking dalam cluster |
| `survey_analysis/reliability/reliability.py` | Cronbach α, Omega ω | Reliabilitas konstruk |
| `survey_analysis/cfa/semopy_model.py` | CFA/SEM (semopy) | Model pengukuran & struktural |
| `survey_analysis/lca/stepmix_model.py` + `runner.py` | LCA (stepmix) | Kelas laten responden |
| `survey_analysis/ml/runner.py` | XGBoost/RF surrogate | Prediksi kelas |
| `survey_analysis/shap/explainer.py` | SHAP | Interpretabilitas |
| `survey_analysis/data/loader.py` | Pivot Response | Matriks responden×item |

---

## 10. Glosarium Singkat

- **DSS** — Decision Support System.
- **CFA** — Confirmatory Factor Analysis.
- **SEM** — Structural Equation Modeling.
- **LCA** — Latent Class Analysis.
- **TOPSIS** — Technique for Order Preference by Similarity to Ideal Solution.
- **SHAP** — SHapley Additive exPlanations.
- **BIC/AIC** — Bayesian/Akaike Information Criterion.
- **RMSEA/SRMR/CFI/TLI** — fit indices SEM.
- **AVE PP** — Average Posterior Probability (kualitas klasifikasi kelas).
- **Polychoric correlation** — korelasi antar item ordinal.
