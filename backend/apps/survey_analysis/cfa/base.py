"""Interface + registry engine CFA/SEM.

Pipeline utama TIDAK boleh tahu detail implementasi engine. Ia hanya memanggil
method di SEMEngine. Menambah engine baru = membuat subclass + mendaftarkan ke
registry — tanpa mengubah pipeline/UI/preprocessing/evaluasi.

Kontrak hasil (engine-agnostic):
- fit_indices()      -> dict {cfi, tli, rmsea, rmsea_ci_low, rmsea_ci_high,
                              srmr, chi2, dof, p_value}
- factor_loadings()  -> DataFrame [construct, item, loading, se, p_value]
- path_coefficients()-> DataFrame [lhs, rhs, est, se, p_value, standardized]
- effects()          -> dict {direct, indirect, total} (DataFrame)
"""

from abc import ABC, abstractmethod

import pandas as pd


class SEMEngine(ABC):
    """Interface konsisten untuk engine SEM (semopy / lavaan / ...)."""

    engine_name = "base"
    estimator_label = ""

    @abstractmethod
    def fit(self, matrix, measurement_only=False, **kwargs):
        """Fit model. Return self (atau raise SEMEngineError bila gagal)."""

    @abstractmethod
    def converged(self) -> bool:
        """Apakah model berhasil konvergen."""

    @abstractmethod
    def fit_indices(self) -> dict:
        """Fit indices (CFI/TLI/RMSEA/SRMR/chi2/df/p)."""

    @abstractmethod
    def factor_loadings(self) -> pd.DataFrame:
        """Factor loading per item (measurement model)."""

    @abstractmethod
    def path_coefficients(self) -> pd.DataFrame:
        """Koefisien jalur struktural (direct effects)."""

    @abstractmethod
    def standardized_estimates(self) -> pd.DataFrame:
        """Tabel estimasi lengkap (semua parameter, standardized)."""


class SEMEngineError(RuntimeError):
    """Error saat engine tidak tersedia atau gagal fit."""


SEM_REGISTRY = {}


def register_engine(cls):
    SEM_REGISTRY[cls.engine_name] = cls
    return cls


def get_sem_engine(name):
    """Factory: kembalikan instance engine berdasarkan nama.

    Raise SEMEngineError bila engine tidak dikenal atau dependency-nya tidak
    tersedia (bukan fallback diam-diam).
    """
    if name not in SEM_REGISTRY:
        raise SEMEngineError(
            f"Engine SEM '{name}' tidak dikenali. "
            f"Tersedia: {sorted(SEM_REGISTRY)}"
        )
    cls = SEM_REGISTRY[name]
    availability = cls.availability_error()
    if availability:
        raise SEMEngineError(f"Engine '{name}' tidak tersedia. {availability}")
    return cls()
