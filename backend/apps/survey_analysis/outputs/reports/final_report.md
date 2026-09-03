# Laporan Analisis Survei — Pipeline SEM/LCA/ML/SHAP

## 1. Kualitas Data
- Responden: **1152**
- Item Likert: **88**
- Nilai invalid (di luar skala): 0
- Missing cells: 0
- Item near-zero variance (flag): 0
- Reverse-coded: belum dikonfirmasi (tidak di-recode otomatis)

## 2. Reliabilitas (Cronbach's Alpha & McDonald's Omega)
| Konstruk | Items | Alpha | Omega | Status |
|---|---|---|---|---|
| X1 Orientasi Pasar | 8 | 0.828 | 0.828 | ok |
| X2 Fasilitas Pariwisata | 8 | 0.824 | 0.824 | ok |
| X3 Infrastruktur dan Aksesibilitas | 8 | 0.814 | 0.814 | ok |
| X4 Hubungan Pemasaran | 8 | 0.827 | 0.827 | ok |
| X5 Kepuasan Pengunjung | 8 | 0.819 | 0.819 | ok |
| Y1 Inovasi Ekonomi Kreatif | 8 | 0.821 | 0.821 | ok |
| Y2 Kualitas Layanan | 8 | 0.810 | 0.810 | ok |
| Y3 Orientasi Kewirausahaan | 8 | 0.824 | 0.824 | ok |
| Z1 Penerimaan Daerah | 8 | 0.808 | 0.808 | ok |
| Z2 Kunjungan Wisata | 8 | 0.824 | 0.824 | ok |
| Z3 Keunggulan Bersaing | 8 | 0.815 | 0.816 | ok |

## 3. CFA (Measurement Model)
- Estimator: ULS (polychoric)
| CFI | TLI | RMSEA | SRMR | Chi² (df) | p |
|---|---|---|---|---|---|
| 0.999 | 0.999 | 0.020 | — | 5379.4 (3685) | 0.0000 |

## 4. SEM (Structural Model)
| CFI | TLI | RMSEA | Chi² (df) |
|---|---|---|---|
| 0.952 | 0.951 | 0.119 | 64074.2 (3706) |

**Path coefficients (24 jalur):**
| Target | Source | Estimate | Std | p |
|---|---|---|---|---|
| Y1 | X1 | 101.92 | 130.80 | 0.0000 |
| Y1 | X2 | 17.36 | 19.85 | 0.0000 |
| Y1 | X3 | 41.80 | 41.58 | 0.0000 |
| Y1 | X4 | -49.93 | -45.75 | 0.0000 |
| Y1 | X5 | -133.25 | -146.19 | 0.0000 |
| Y2 | X1 | 58.15 | 69.70 | 0.0000 |
| Y2 | X2 | 5.54 | 5.92 | 0.0000 |
| Y2 | X3 | 20.42 | 18.98 | 0.0000 |
| Y2 | X4 | -15.07 | -12.90 | 0.0000 |
| Y2 | X5 | -79.05 | -81.01 | 0.0000 |
| Y3 | X1 | 119.74 | 133.97 | 0.0000 |
| Y3 | X2 | 27.32 | 27.23 | 0.0000 |
| Y3 | X3 | 32.98 | 28.60 | 0.0000 |
| Y3 | X4 | -57.08 | -45.59 | 0.0000 |
| Y3 | X5 | -150.59 | -144.03 | 0.0000 |
| Z1 | Y1 | -0.97 | -295.18 | 0.0000 |
| Z1 | Y2 | -7.59 | -2463.02 | 0.0000 |
| Z1 | Y3 | 7.93 | 2757.21 | 0.0000 |
| Z2 | Y1 | 318.37 | 282.98 | 0.0000 |
| Z2 | Y2 | 71.57 | 68.11 | 0.0000 |
| Z2 | Y3 | -343.39 | -350.09 | 0.0000 |
| Z3 | Y1 | 33.14 | 11727.15 | 0.0000 |
| Z3 | Y2 | 8.35 | 3163.12 | 0.0000 |
| Z3 | Y3 | -36.69 | -14891.26 | 0.0000 |

## 5. LCA (Latent Class Analysis)
| Kelas | AIC | BIC | LogLik | Entropy | Min class % |
|---|---|---|---|---|---|
| 2 | 228538.3 | 232986.7 | -98.427 | 1.000 | 46.1 |
| 3 | 216198.0 | 222873.1 | -92.688 | 1.000 | 20.6 |
| 4 | 216799.7 | 225701.5 | -92.567 | 0.994 | 5.1 |
| 5 | 215506.3 | 226634.9 | -91.623 | 1.000 | 2.0 |
| 6 | 218121.4 | 231476.7 | -92.375 | 0.978 | 1.9 |

**Terpilih: 3 kelas.** BIC terendah pada 3 kelas

| Kelas | Size | % | Ave posterior prob |
|---|---|---|---|
| 0 | 531 | 46.09% | 1.0 |
| 1 | 384 | 33.33% | 1.0 |
| 2 | 237 | 20.57% | 1.0 |

## 6. Surrogate Machine Learning
| Model | Accuracy | Macro F1 | Best params |
|---|---|---|---|
| xgboost | 1.000 | 1.000 | {'colsample_bytree': 0.8, 'learning_rate': 0.1, 'max_depth': 3, 'n_estimators': 200, 'subsample': 0.8} |
| random_forest | 1.000 | 1.000 | {'max_depth': None, 'n_estimators': 100} |

## 7. SHAP (Feature Importance)
| Rank | Item | Mean \|SHAP\| | Direction | Most affected class |
|---|---|---|---|---|
| 1 | X1.8 | 0.201 | negative | 0 |
| 2 | Z1.2 | 0.146 | negative | 0 |
| 3 | Z2.5 | 0.142 | negative | 0 |
| 4 | X4.4 | 0.132 | negative | 0 |
| 5 | X5.8 | 0.129 | negative | 1 |
| 6 | X4.3 | 0.129 | negative | 2 |
| 7 | Z2.1 | 0.123 | negative | 0 |
| 8 | Y1.5 | 0.115 | negative | 1 |
| 9 | X1.4 | 0.115 | negative | 1 |
| 10 | Z1.3 | 0.108 | negative | 0 |

## 8. Kesimpulan
> SHAP dan ML bersifat **asosiatif/deskriptif**, BUKAN kausal.

- Temuan statistik (reliabilitas & CFA) — lihat bagian 2–3.
- Temuan segmentasi (LCA) — lihat bagian 5.
- Temuan ML (surrogate) — lihat bagian 6.
- Interpretasi SHAP — lihat bagian 7.
