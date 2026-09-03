"""Tahap 2 — Reliabilitas konstruk.

Menghitung Cronbach's Alpha dan McDonald's Omega (omega_total) per konstruk.
Implementasi manual yang tervalidasi (formula standar; Omega via model
1-faktor). Tidak ada drop item otomatis.

STOP condition: bila Alpha ATAU Omega < threshold (default 0.60), pipeline
berhenti dan meminta review item — tidak lanjut ke CFA.
"""

import numpy as np
import pandas as pd
from sklearn.decomposition import FactorAnalysis

from apps.survey_analysis.config import settings as cfg
from apps.survey_analysis.config import model_config


def interpret(value):
    """Interpretasi reliabilitas (Alpha/Omega)."""
    if value is None or np.isnan(value):
        return "problematic"
    if value >= 0.70:
        return "acceptable"
    if value >= 0.60:
        return "questionable"
    return "problematic"


def cronbach_alpha(items):
    """Cronbach's Alpha (formula standar, listwise deletion)."""
    items = items.dropna()  # listwise: buang baris dengan missing pada konstruk ini
    if len(items) < 3 or items.shape[1] < 2:
        return None, len(items)
    k = items.shape[1]
    var_items = items.var(axis=0, ddof=1).sum()
    var_total = items.sum(axis=1).var(ddof=1)
    if var_total == 0:
        return None, len(items)
    alpha = (k / (k - 1)) * (1 - var_items / var_total)
    return float(alpha), len(items)


def mcdonald_omega(items):
    """McDonald's omega_total (model 1-faktor ML, loadings terstandarisasi)."""
    items = items.dropna()
    if len(items) < 3 or items.shape[1] < 2:
        return None, len(items)
    X = items.values.astype(float)
    sd = X.std(axis=0, ddof=1)
    sd[sd == 0] = 1.0
    Z = (X - X.mean(axis=0)) / sd

    fa = FactorAnalysis(
        n_components=1,
        rotation=None,
        random_state=cfg.RANDOM_STATE,
    )
    fa.fit(Z)
    loadings = np.asarray(fa.components_[0], dtype=float)

    sum_loading = float(loadings.sum())
    sum_unique = float((1.0 - loadings ** 2).sum())
    denom = sum_loading ** 2 + sum_unique
    if denom == 0:
        return None, len(items)
    omega = (sum_loading ** 2) / denom
    return float(omega), len(items)


def run_reliability(matrix):
    """Hitung reliabilitas tiap konstruk + lakukan STOP check.

    Return dict dengan:
      - results : DataFrame (construct, name, n_items, alpha, omega, status)
      - passed  : bool (False bila ada alpha/omega < threshold)
      - message : pesan bila STOP
    """
    rows = []
    failed = []

    for code in model_config.construct_order():
        cfg_items = model_config.CONSTRUCTS[code]["items"]
        cols = [c for c in cfg_items if c in matrix.columns]
        if not cols:
            rows.append({
                "construct": code,
                "name": model_config.name_of(code),
                "n_items": 0,
                "cronbach_alpha": None,
                "omega": None,
                "n_used": 0,
                "status": "no-data",
            })
            failed.append(code)
            continue

        sub = matrix[cols]
        alpha, n_used = cronbach_alpha(sub)
        omega, _ = mcdonald_omega(sub)

        alpha_bad = alpha is None or alpha < cfg.RELIABILITY_THRESHOLD
        omega_bad = omega is None or omega < cfg.RELIABILITY_THRESHOLD
        if alpha_bad or omega_bad:
            status = "problematic"
            failed.append(code)
        else:
            status = "ok"

        rows.append({
            "construct": code,
            "name": model_config.name_of(code),
            "n_items": len(cols),
            "cronbach_alpha": round(alpha, 4) if alpha is not None else None,
            "omega": round(omega, 4) if omega is not None else None,
            "n_used": int(n_used),
            "status": status,
        })

    results = pd.DataFrame(rows)
    passed = len(failed) == 0

    message = None
    if not passed:
        names = ", ".join(f"{c} ({model_config.name_of(c)})" for c in failed)
        message = (
            "Reliabilitas konstruk tidak memenuhi threshold "
            f"(alpha/omega < {cfg.RELIABILITY_THRESHOLD}): {names}. "
            "Review item diperlukan sebelum CFA."
        )

    return {"results": results, "passed": passed, "message": message}
