"""Runner surrogate ML: split → train → evaluate → STOP check.

Memprediksi label kelas LCA dari raw Likert items. Split 80/20 stratified,
random_state eksplisit. STOP sebelum SHAP bila accuracy < 0.80.
"""

import numpy as np
from sklearn.model_selection import train_test_split

from apps.survey_analysis.config import settings as cfg
from apps.survey_analysis.ml.base import get_ml_model
from apps.survey_analysis.ml.evaluation import evaluate, cross_val_accuracy


def split(matrix, class_labels, test_size=None, random_state=None):
    """Split 80/20 stratified. Return (X_train, X_test, y_train, y_test)."""
    test_size = test_size if test_size is not None else cfg.ML_TEST_SIZE
    random_state = random_state if random_state is not None else cfg.RANDOM_STATE
    X = matrix.values.astype(float)
    y = np.asarray(class_labels, dtype=int)
    return train_test_split(
        X, y,
        test_size=test_size,
        stratify=y,
        random_state=random_state,
    )


def run_surrogate_ml(matrix, class_labels, engines=("xgboost", "random_forest"),
                     random_state=None):
    """Latih + evaluasi semua model surrogate. Return dict hasil."""
    random_state = random_state if random_state is not None else cfg.RANDOM_STATE
    X_train, X_test, y_train, y_test = split(
        matrix, class_labels, random_state=random_state
    )

    results = {}
    for name in engines:
        model = get_ml_model(name)
        model.fit(X_train, y_train, cv_folds=cfg.ML_CV_FOLDS, random_state=random_state)
        metrics = evaluate(model, X_test, y_test)
        metrics["best_params"] = getattr(model, "best_params_", None)
        metrics["model"] = model
        results[name] = metrics

    return {
        "results": results,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "feature_names": list(matrix.columns),
    }


def should_proceed(results, accuracy_min=None):
    """Apakah surrogate ML layak lanjut ke SHAP (accuracy >= threshold)."""
    accuracy_min = accuracy_min if accuracy_min is not None else cfg.ML_ACCURACY_MIN
    # Pakai model utama (xgboost) sebagai acuan.
    primary = results.get("xgboost") or next(iter(results.values()))
    acc = primary["accuracy"]
    return acc >= accuracy_min, acc
