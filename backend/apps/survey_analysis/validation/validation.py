"""Tahap 1 — Validasi data.

Memeriksa integritas data sebelum analisis lanjut:
- tipe data & range Likert (nilai di luar skala = invalid),
- missing values (per item + per responden + pola),
- near-zero variance (flag, TIDAK auto-drop),
- normalitas (Shapiro-Wilk) — hanya informatif, TIDAK dipakai untuk
  mengubah data ordinal menjadi kontinu.

Tidak ada penghapusan otomatis: semua temuan hanya di-flag untuk review.
"""

import numpy as np
import pandas as pd
from scipy import stats

from apps.survey_analysis.config import settings as cfg
from apps.survey_analysis.config import model_config


# ---------- Tipe & range ----------

def type_range_report(matrix):
    """Per item: dtype, min, max, unique, nilai invalid (di luar skala)."""
    rows = []
    for col in matrix.columns:
        s = matrix[col]
        invalid = s.dropna()
        invalid = invalid[(invalid < cfg.LIKERT_MIN) | (invalid > cfg.LIKERT_MAX)]
        rows.append({
            "item": col,
            "dtype": str(s.dtype),
            "minimum": float(s.min()) if s.notna().any() else None,
            "maximum": float(s.max()) if s.notna().any() else None,
            "unique_values": int(s.nunique(dropna=True)),
            "invalid_count": int(invalid.shape[0]),
        })
    return pd.DataFrame(rows)


# ---------- Missing values ----------

def missing_report(matrix):
    """Missing per item, per responden, dan pola missing."""
    per_item = matrix.isna().sum().rename("missing_count").reset_index()
    per_item.columns = ["item", "missing_count"]
    per_item["missing_pct"] = (per_item["missing_count"] / matrix.shape[0]) * 100

    per_respondent = matrix.isna().sum(axis=1)
    n_resp_with_missing = int((per_respondent > 0).sum())

    return {
        "per_item": per_item,
        "per_respondent_summary": {
            "n_respondents": int(matrix.shape[0]),
            "n_respondents_with_missing": n_resp_with_missing,
            "pct_respondents_with_missing": n_resp_with_missing / matrix.shape[0] * 100,
            "total_missing_cells": int(matrix.isna().sum().sum()),
        },
        # Pola: item mana yang hilang bersamaan (korelasi missing sederhana).
        "missing_pattern": _missing_pattern(matrix),
    }


def _missing_pattern(matrix):
    """Item yang paling sering hilang bersamaan (top kombinasi, sederhana)."""
    # Hanya hitung item yang punya missing; korelasi keberadaan missing.
    miss = matrix.isna()
    cols_with_missing = miss.columns[miss.any()].tolist()
    if len(cols_with_missing) <= 1:
        return []
    sub = miss[cols_with_missing].astype(int)
    corr = sub.corr().round(2)
    out = []
    for i in range(len(cols_with_missing)):
        for j in range(i + 1, len(cols_with_missing)):
            a, b = cols_with_missing[i], cols_with_missing[j]
            out.append({"item_a": a, "item_b": b, "corr": float(corr.loc[a, b])})
    out.sort(key=lambda r: -abs(r["corr"]))
    return out[:10]


# ---------- Near-zero variance ----------

def variance_report(matrix):
    """Item dengan varians sangat kecil (flag, bukan auto-drop)."""
    rows = []
    for col in matrix.columns:
        s = matrix[col].dropna()
        var = float(s.var(ddof=1)) if len(s) > 1 else 0.0
        pct_dominant = float(s.value_counts(normalize=True).iloc[0]) if len(s) else 1.0
        rows.append({
            "item": col,
            "variance": var,
            "std": float(s.std(ddof=1)) if len(s) > 1 else 0.0,
            "pct_dominant_category": pct_dominant,
            "flag_near_zero": bool(var < 0.05 or pct_dominant > 0.95),
        })
    return pd.DataFrame(rows)


# ---------- Normality (informatif) ----------

def normality_report(matrix, max_sample=5000):
    """Shapiro-Wilk per item. Hanya informatif — data Likert tetap ordinal."""
    rows = []
    for col in matrix.columns:
        s = matrix[col].dropna()
        if len(s) < 3:
            rows.append({"item": col, "statistic": None, "p_value": None,
                         "interpretation": "insufficient"})
            continue
        # Shapiro-Wilk sensitif terhadap n besar; batasi sampel (acak, seed).
        if len(s) > max_sample:
            s = s.sample(max_sample, random_state=cfg.RANDOM_STATE)
        w, p = stats.shapiro(s.astype(float))
        rows.append({
            "item": col,
            "statistic": float(w),
            "p_value": float(p),
            "interpretation": "normal" if p > 0.05 else "non-normal",
        })
    return pd.DataFrame(rows)


# ---------- Reverse-coded ----------

def reverse_coded_status():
    """Status reverse-coded items (belum dikonfirmasi = flag)."""
    if model_config.REVERSE_ITEMS:
        return {
            "confirmed": True,
            "items": model_config.REVERSE_ITEMS,
        }
    return {
        "confirmed": False,
        "warning": "Reverse-coded item belum dikonfirmasi — tidak dilakukan recoding otomatis.",
    }


# ---------- Orkestrasi ----------

def run_validation(matrix):
    """Jalankan seluruh pemeriksaan validasi. Return dict hasil terstruktur."""
    type_range = type_range_report(matrix)
    missing = missing_report(matrix)
    variance = variance_report(matrix)
    normality = normality_report(matrix)
    reverse = reverse_coded_status()

    n_invalid = int(type_range["invalid_count"].sum())
    n_near_zero = int(variance["flag_near_zero"].sum())
    n_missing_cells = missing["per_respondent_summary"]["total_missing_cells"]

    return {
        "summary": {
            "n_respondents": int(matrix.shape[0]),
            "n_items": int(matrix.shape[1]),
            "n_invalid_values": n_invalid,
            "n_missing_cells": n_missing_cells,
            "n_near_zero_items": n_near_zero,
            "n_items_with_missing": int((missing["per_item"]["missing_count"] > 0).sum()),
            "reverse_coded": reverse,
        },
        "type_range": type_range,
        "missing": missing,
        "variance": variance,
        "normality": normality,
        "reverse_coded": reverse,
    }
