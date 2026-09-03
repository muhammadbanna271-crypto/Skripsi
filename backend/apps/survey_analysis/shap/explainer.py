"""Interpretasi SHAP untuk surrogate ML (TreeExplainer, XGBoost terbaik).

Menangani API SHAP modern (shap_values multi-kelas berbentuk list of arrays)
dengan validasi shape sebelum menghitung/ploting. Output bersifat DESKRIPTIF
(asosiatif), BUKAN kausal.
"""

import numpy as np
import pandas as pd


def explain(model, X, feature_names):
    """Hitung SHAP values pada X untuk model (XGBoost/RF).

    Return dict {shap_values, base_values, n_classes}.
    shap_values: list of ndarray, satu (n_samples, n_features) per kelas.
    Menangani variasi bentuk output SHAP antar versi (list vs ndarray 3D).
    """
    import shap
    # Wrapper model ML kita menyimpan estimator mentah di ._model.
    estimator = getattr(model, "_model", model)
    explainer = shap.TreeExplainer(estimator)
    raw = explainer.shap_values(X)

    # Normalisasi ke list of (n_samples, n_features), satu elemen per kelas.
    if isinstance(raw, list):
        sv_list = [np.asarray(a) for a in raw]
    else:
        raw = np.asarray(raw)
        if raw.ndim == 3:
            # (n_samples, n_features, n_classes) -> per kelas.
            sv_list = [raw[:, :, c] for c in range(raw.shape[2])]
        elif raw.ndim == 2:
            sv_list = [raw]
        else:
            raise ValueError(f"Shape SHAP tak terduga: {raw.shape}")

    # Validasi shape sebelum dipakai.
    for arr in sv_list:
        if arr.shape != X.shape:
            raise ValueError(
                f"Shape SHAP tidak valid: {arr.shape} vs data {X.shape}"
            )

    return {
        "shap_values": sv_list,
        "base_values": explainer.expected_value,
        "n_classes": len(sv_list),
    }


def feature_importance(shap_values, feature_names):
    """Global feature importance (mean |SHAP| per fitur, rata-rata antar kelas).

    Return DataFrame [feature, mean_abs_shap, rank].
    """
    # shap_values: list (n_classes) of (n_samples, n_features).
    mean_abs = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
    df = pd.DataFrame({
        "feature": feature_names,
        "mean_abs_shap": mean_abs,
    }).sort_values("mean_abs_shap", ascending=False)
    df["rank"] = range(1, len(df) + 1)
    return df


def per_class_importance(shap_values, feature_names, class_labels):
    """Mean |SHAP| per fitur per kelas (class importance)."""
    rows = []
    for c, sv in enumerate(shap_values):
        mean_abs = np.abs(sv).mean(axis=0)
        for j, f in enumerate(feature_names):
            rows.append({
                "class": class_labels[c] if class_labels is not None else c,
                "feature": f,
                "mean_abs_shap": float(mean_abs[j]),
            })
    return pd.DataFrame(rows)


def direction_and_class(shap_values, feature_names, class_labels):
    """Arah dominan + kelas paling terdampak per fitur.

    Arah dominan = tanda rata-rata SHAP global (pos/neg). Kelas paling
    terdampak = kelas dengan mean |SHAP| terbesar untuk fitur tsb.
    """
    stacked = np.stack(shap_values)  # (n_classes, n_samples, n_features)
    n_classes = stacked.shape[0]
    rows = []
    for j, f in enumerate(feature_names):
        global_mean = stacked[:, :, j].mean()
        dominant = "positive" if global_mean >= 0 else "negative"
        class_abs = np.abs(stacked[:, :, j]).mean(axis=1)  # per kelas
        most = int(np.argmax(class_abs))
        rows.append({
            "feature": f,
            "dominant_direction": dominant,
            "most_affected_class": class_labels[most] if class_labels is not None else most,
        })
    return pd.DataFrame(rows)


def summary_table(shap_values, feature_names, class_labels=None):
    """Tabel ringkasan SHAP: item, mean_abs_shap, arah, kelas terdampak, rank."""
    imp = feature_importance(shap_values, feature_names)
    dirs = direction_and_class(shap_values, feature_names, class_labels)
    merged = imp.merge(dirs, on="feature", how="left")
    return merged


def top_features(summary, n=5):
    """Fitur (item) dengan mean |SHAP| tertinggi."""
    return summary.head(n)
