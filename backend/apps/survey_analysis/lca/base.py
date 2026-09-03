"""Interface + registry engine LCA (Latent Class Analysis).

LCA memakai RAW item Likert (bukan factor scores / skor kontinu). Engine
saat ini: StepMix. Menambah engine lain = subclass LCAEngine + daftarkan.
"""

from abc import ABC, abstractmethod

import pandas as pd


class LCAEngine(ABC):
    engine_name = "base"

    @abstractmethod
    def fit(self, matrix, n_classes, random_state, **kwargs):
        """Fit model LCA pada matriks raw item. Return self."""

    @abstractmethod
    def predict_proba(self, matrix) -> pd.DataFrame:
        """Posterior probability keanggotaan kelas (n_respondents x n_classes)."""

    @abstractmethod
    def predict_class(self, matrix) -> pd.Series:
        """Hard assignment kelas per responden."""

    @abstractmethod
    def bic(self, matrix) -> float: ...

    @abstractmethod
    def aic(self, matrix) -> float: ...

    @abstractmethod
    def log_likelihood(self, matrix) -> float: ...

    @abstractmethod
    def relative_entropy(self) -> float: ...

    @abstractmethod
    def item_probabilities(self) -> pd.DataFrame:
        """Probabilitas respons item per kelas (conditional item probabilities)."""


class LCAEngineError(RuntimeError):
    pass


LCA_REGISTRY = {}


def register_lca(cls):
    LCA_REGISTRY[cls.engine_name] = cls
    return cls


def get_lca_engine(name):
    if name not in LCA_REGISTRY:
        raise LCAEngineError(
            f"Engine LCA '{name}' tidak dikenali. Tersedia: {sorted(LCA_REGISTRY)}"
        )
    cls = LCA_REGISTRY[name]
    availability = cls.availability_error()
    if availability:
        raise LCAEngineError(f"Engine '{name}' tidak tersedia. {availability}")
    return cls()
