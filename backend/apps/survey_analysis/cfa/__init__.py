"""Paket CFA/SEM: registry engine + factory.

Menambah engine baru = tulis adapter (subclass SEMEngine) lalu daftarkan di
sini. Pipeline/UI memanggil ``get_sem_engine(name)`` dan tidak tahu detail
implementasi.
"""

from apps.survey_analysis.cfa.base import (
    SEMEngine,
    SEMEngineError,
    SEM_REGISTRY,
    get_sem_engine,
)
from apps.survey_analysis.cfa.semopy_model import SemopySEM
from apps.survey_analysis.cfa.lavaan_model import LavaanSEM

# Registrasi engine (idempoten). Tambah engine baru di sini.
SEM_REGISTRY.update({
    "semopy": SemopySEM,
    "lavaan": LavaanSEM,
})

__all__ = [
    "SEMEngine",
    "SEMEngineError",
    "SEM_REGISTRY",
    "get_sem_engine",
    "SemopySEM",
    "LavaanSEM",
]
