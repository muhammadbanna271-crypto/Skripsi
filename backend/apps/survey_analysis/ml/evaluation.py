"""Evaluasi model surrogate ML (engine-agnostic)."""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)


def evaluate(model, X_test, y_test, class_names=None):
    """Evaluasi model pada test set.

    Return dict {accuracy, macro_f1, per_class, confusion_matrix, report}.
    """
    y_pred = model.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro"))

    labels = sorted(set(y_test))
    report = classification_report(
        y_test, y_pred, labels=labels, output_dict=True, zero_division=0
    )
    per_class = [
        {
            "class": int(lbl),
            "precision": report[str(lbl)]["precision"],
            "recall": report[str(lbl)]["recall"],
            "f1": report[str(lbl)]["f1-score"],
        }
        for lbl in labels
    ]

    cm = confusion_matrix(y_test, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=labels, columns=labels)

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "confusion_matrix": cm_df,
        "class_names": class_names or [str(l) for l in labels],
    }


def cross_val_accuracy(model, X, y, cv_folds=5):
    """Cross-validation accuracy (stratified) pada data penuh."""
    from sklearn.model_selection import cross_val_score
    scores = cross_val_score(model, X, y, cv=cv_folds, scoring="accuracy")
    return {
        "mean": float(np.mean(scores)),
        "std": float(np.std(scores)),
        "scores": [float(s) for s in scores],
    }
