"""Pengaturan global pipeline analisis survei.

Semua nilai yang bisa berubah (seed, threshold, ukuran split, path output)
disimpan di sini supaya reproducible dan bisa di-audit tanpa mengubah kode.
"""

from pathlib import Path

# ---------- Reproducibility ----------
RANDOM_STATE = 42  # satu seed eksplisit untuk seluruh pipeline.

# ---------- Skala Likert ----------
LIKERT_MIN = 1
LIKERT_MAX = 5
LIKERT_LABELS = {
    1: "Sangat Tidak Setuju",
    2: "Tidak Setuju",
    3: "Netral",
    4: "Setuju",
    5: "Sangat Setuju",
}

# ---------- Reliability ----------
# STOP bila Alpha ATAU Omega < threshold ini.
RELIABILITY_THRESHOLD = 0.60

# ---------- CFA fit (Hu & Bentler, 1999) ----------
CFA_CFI_MIN = 0.95
CFA_TLI_MIN = 0.95
CFA_RMSEA_MAX = 0.06
CFA_SRMR_MAX = 0.08

# ---------- Factor loading ----------
LOADING_IDEAL = 0.70
LOADING_ACCEPTABLE = 0.50

# ---------- LCA ----------
LCA_CLASS_RANGE = [2, 3, 4, 5, 6]
LCA_ENTROPY_MIN = 0.80
LCA_AVEPP_MIN = 0.70

# ---------- Surrogate ML ----------
ML_TRAIN_SIZE = 0.80
ML_TEST_SIZE = 0.20
ML_CV_FOLDS = 5
ML_ACCURACY_MIN = 0.80  # STOP sebelum SHAP bila accuracy < 0.80.

# ---------- Output ----------
# Self-contained: outputs/ relatif terhadap paket survey_analysis.
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

# Subdirektori output (dibuat otomatis oleh exporter).
OUTPUT_SUBDIRS = [
    "validation",
    "reliability",
    "cfa",
    "lca",
    "ml",
    "shap",
    "reports",
]
