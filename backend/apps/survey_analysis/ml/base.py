"""Interface + registry model ML surrogate.

Surrogate ML memprediksi label kelas LCA dari raw Likert items (bukan factor
scores). Interface konsisten supaya model bisa dipilih via UI tanpa mengubah
pipeline. Preprocessing/split/evaluasi SAMA untuk semua model.
"""

from abc import ABC, abstractmethod


class MLModel(ABC):
    model_name = "base"

    @abstractmethod
    def fit(self, X_train, y_train, **kwargs):
        """Latih model. Return self."""

    @abstractmethod
    def predict(self, X):
        """Prediksi kelas (hard)."""

    @abstractmethod
    def predict_proba(self, X):
        """Probabilitas kelas (untuk SHAP/soft)."""


class MLEngineError(RuntimeError):
    pass


ML_REGISTRY = {}


def register_ml(cls):
    ML_REGISTRY[cls.model_name] = cls
    return cls


def get_ml_model(name):
    if name not in ML_REGISTRY:
        raise MLEngineError(
            f"Model ML '{name}' tidak dikenali. Tersedia: {sorted(ML_REGISTRY)}"
        )
    cls = ML_REGISTRY[name]
    availability = cls.availability_error()
    if availability:
        raise MLEngineError(f"Model '{name}' tidak tersedia. {availability}")
    return cls()
