"""Diagnostik CFA/SEM: evaluasi fit, loading, dan efek (direct/indirect/total).

Engine-agnostic — beroperasi pada hasil terstandarisasi yang sudah diekstrak
oleh adapter (DataFrame path_coefficients / factor_loadings + dict fit_indices),
sehingga tidak bergantung pada semopy/lavaan.
"""

from collections import defaultdict

import numpy as np
import pandas as pd

from apps.survey_analysis.config import settings as cfg
from apps.survey_analysis.config import model_config


# ---------- Fit indices ----------

def evaluate_fit(fit_indices):
    """Evaluasi fit indices terhadap kriteria Hu & Bentler (1999).

    Return list of {index, value, criterion, passed}.
    """
    checks = [
        ("CFI", fit_indices.get("cfi"), cfg.CFA_CFI_MIN, "greater"),
        ("TLI", fit_indices.get("tli"), cfg.CFA_TLI_MIN, "greater"),
        ("RMSEA", fit_indices.get("rmsea"), cfg.CFA_RMSEA_MAX, "less"),
        ("SRMR", fit_indices.get("srmr"), cfg.CFA_SRMR_MAX, "less"),
    ]
    out = []
    for name, value, threshold, direction in checks:
        if value is None:
            out.append({"index": name, "value": None,
                        "criterion": f"{'>' if direction == 'greater' else '<'} {threshold}",
                        "passed": None})
            continue
        passed = value > threshold if direction == "greater" else value < threshold
        out.append({"index": name, "value": round(value, 4),
                    "criterion": f"{'>' if direction == 'greater' else '<'} {threshold}",
                    "passed": bool(passed)})
    return out


def fit_passed(fit_indices, require_srmr=True):
    """Apakah semua kriteria fit terpenuhi (None = belum tahu -> dianggap gagal)."""
    for c in evaluate_fit(fit_indices):
        if c["passed"] is False:
            return False
        if require_srmr and c["passed"] is None:
            return False
    return True


# ---------- Factor loadings ----------

def evaluate_loadings(loadings_df):
    """Flag factor loading tiap item (problematic / acceptable / ideal)."""
    if loadings_df.empty:
        return loadings_df
    df = loadings_df.copy()
    df["loading"] = pd.to_numeric(df["loading"], errors="coerce")

    def flag(x):
        if x is None or pd.isna(x):
            return "unknown"
        if x < cfg.LOADING_ACCEPTABLE:
            return "problematic"
        if x < cfg.LOADING_IDEAL:
            return "acceptable"
        return "ideal"

    df["flag"] = df["loading"].apply(flag)
    return df


# ---------- Efek (direct / indirect / total) ----------

def compute_effects(path_df, standardized=True):
    """Hitung efek langsung/tak langsung/total dari koefisien jalur.

    path_df : DataFrame [lhs (target), rhs (source), est, se, p_value, standardized].
    standardized=True -> pakai koefisien terstandarisasi.

    Return dict dengan key 'direct', 'indirect', 'total' (DataFrame) yang
    berisi kolom [source, target, via, effect].
    """
    col = "standardized" if standardized and "standardized" in path_df.columns else "est"
    coef = {}
    for _, row in path_df.iterrows():
        src, dst = row["rhs"], row["lhs"]
        v = row[col]
        coef[(src, dst)] = float(v) if v is not None and not pd.isna(v) else np.nan

    # Direct = jalur yang ada di config.
    direct_rows = []
    for src, dst in model_config.PATHS:
        direct_rows.append({
            "source": src,
            "target": dst,
            "via": "",
            "effect": coef.get((src, dst)),
        })

    # Indirect = X -> Y -> Z (full mediation; tidak ada X -> Z langsung).
    indirect_rows = []
    for x in model_config.EXOGENOUS:
        for z in model_config.OUTCOMES:
            total = 0.0
            for y in model_config.MEDIATORS:
                a = coef.get((x, y))
                b = coef.get((y, z))
                if a is None or b is None or np.isnan(a) or np.isnan(b):
                    continue
                total += a * b
                indirect_rows.append({
                    "source": x,
                    "target": z,
                    "via": y,
                    "effect": round(a * b, 4),
                })
            indirect_rows.append({
                "source": x,
                "target": z,
                "via": "(total mediasi)",
                "effect": round(total, 4) if total else None,
            })

    # Total = direct + indirect.
    total_rows = []
    for src, dst in model_config.PATHS:
        direct = coef.get((src, dst))
        indirect = 0.0
        # Untuk X -> Z (tidak ada di PATHS), total = indirect via mediator.
        total_rows.append({
            "source": src,
            "target": dst,
            "effect": round(direct, 4) if direct is not None else None,
        })
    for x in model_config.EXOGENOUS:
        for z in model_config.OUTCOMES:
            total = 0.0
            for y in model_config.MEDIATORS:
                a = coef.get((x, y))
                b = coef.get((y, z))
                if a is None or b is None or np.isnan(a) or np.isnan(b):
                    continue
                total += a * b
            total_rows.append({
                "source": x,
                "target": z,
                "effect": round(total, 4) if total else None,
            })

    return {
        "direct": pd.DataFrame(direct_rows),
        "indirect": pd.DataFrame(indirect_rows),
        "total": pd.DataFrame(total_rows),
    }


def mediation_summary(indirect_df):
    """Ringkas mediasi X -> Z (hanya jalur gabungan, tanpa via per mediator)."""
    df = indirect_df[indirect_df["via"] == "(total mediasi)"].copy()
    df = df.rename(columns={"effect": "indirect_effect"})
    return df[["source", "target", "indirect_effect"]]
