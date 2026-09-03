"""Runner LCA: perbandingan jumlah kelas, seleksi, diagnostik, dan profil.

Semua berbasis RAW Likert items (bukan factor scores). Pemilihan jumlah kelas
memakai BIC sebagai kriteria utama, tapi dikombinasikan dengan entropy,
ukuran kelas minimum, dan interpretability — tidak hanya BIC.
"""

import numpy as np
import pandas as pd

from apps.survey_analysis.config import settings as cfg
from apps.survey_analysis.config import model_config
from apps.survey_analysis.lca.base import get_lca_engine


def fit_models(matrix, class_range=None, random_state=None, engine="stepmix"):
    """Fit model LCA untuk rentang jumlah kelas. Return (comparison_df, models)."""
    class_range = class_range or cfg.LCA_CLASS_RANGE
    random_state = random_state if random_state is not None else cfg.RANDOM_STATE

    rows = []
    models = {}
    for k in class_range:
        eng = get_lca_engine(engine)
        eng.fit(matrix, n_classes=k, random_state=random_state)
        models[k] = eng
        rows.append({
            "classes": int(k),
            "aic": eng.aic(matrix),
            "bic": eng.bic(matrix),
            "log_likelihood": eng.log_likelihood(matrix),
            "entropy": eng.relative_entropy(),
        })

    comparison = pd.DataFrame(rows)
    comparison["min_class_pct"] = [
        _min_class_pct(models[k], matrix) for k in class_range
    ]
    return comparison, models


def _min_class_pct(engine, matrix):
    hard = engine.predict_class(matrix)
    counts = hard.value_counts(normalize=True)
    return float(counts.min()) * 100 if len(counts) else 0.0


def select_classes(comparison):
    """Pilih jumlah kelas terbaik (BIC utama + entropy + ukuran kelas).

    Return dict {selected, reason, review_required}.
    """
    best_bic_idx = comparison["bic"].idxmin()
    best_bic = comparison.loc[best_bic_idx, "classes"]
    row = comparison.loc[best_bic_idx]

    reasons = []
    review = False

    # BIC utama.
    reasons.append(f"BIC terendah pada {int(best_bic)} kelas")

    # Entropy > 0.80.
    if row["entropy"] < cfg.LCA_ENTROPY_MIN:
        reasons.append(f"entropy {row['entropy']:.3f} < {cfg.LCA_ENTROPY_MIN}")
        review = True

    # Ukuran kelas minimum.
    if row["min_class_pct"] < 5.0:
        reasons.append(f"kelas terkecil hanya {row['min_class_pct']:.1f}%")
        review = True

    # BIC masih menurun di kelas tertinggi (indikasi bisa lebih banyak kelas).
    max_classes = comparison["classes"].max()
    if int(best_bic) == int(max_classes):
        reasons.append(f"BIC terendah di batas atas ({int(max_classes)} kelas)")
        review = True

    return {
        "selected": int(best_bic),
        "reason": "; ".join(reasons),
        "review_required": review,
    }


def classification_diagnostics(engine, matrix):
    """Diagnostik klasifikasi per kelas + entropy."""
    proba = engine.predict_proba(matrix)
    hard = engine.predict_class(matrix).astype(int)

    rows = []
    for c in range(engine.n_classes):
        mask = (hard == c).values
        size = int(mask.sum())
        avepp = float(proba.values[mask, c].mean()) if size else 0.0
        rows.append({
            "class": c,
            "class_size": size,
            "class_percentage": round(size / len(hard) * 100, 2),
            "average_posterior_probability": round(avepp, 3),
        })
    return pd.DataFrame(rows), engine.relative_entropy()


def conditional_probabilities(engine):
    """Probabilitas respons item per kelas (raw, dari stepmix)."""
    return engine.item_probabilities()


def class_profiles(engine, matrix, top_n=5):
    """Profil substantif per kelas: item dengan tingkat persetujuan tertinggi.

    Persetujuan = P(kategori >= 4). Berasal dari conditional probabilities,
    bukan asumsi.
    """
    proba = engine.predict_proba(matrix)
    hard = engine.predict_class(matrix).astype(int)
    mm = engine.item_probabilities()

    # mm: kolom class, item, category, probability.
    # Hitung P(agree) per item per kelas = sum(P(cat) untuk cat>=4).
    mm["category"] = pd.to_numeric(mm["category"], errors="coerce")
    agree = (
        mm[mm["category"] >= (cfg.LIKERT_MAX - 1)]
        .groupby(["class", "item"])["probability"]
        .sum()
        .reset_index()
    )

    profiles = {}
    for c in range(engine.n_classes):
        sub = agree[agree["class"] == c].sort_values("probability", ascending=False)
        top = sub.head(top_n)
        profiles[c] = [
            {
                "item": row["item"],
                "construct": _construct_of(row["item"]),
                "agreement_prob": round(float(row["probability"]), 3),
            }
            for _, row in top.iterrows()
        ]
    return profiles


def _construct_of(item):
    for code in model_config.CONSTRUCTS:
        if item in model_config.CONSTRUCTS[code]["items"]:
            return code
    return None
