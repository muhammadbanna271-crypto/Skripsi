"""Paket LCA: registry engine + factory."""

from apps.survey_analysis.lca.base import (
    LCAEngine,
    LCAEngineError,
    LCA_REGISTRY,
    get_lca_engine,
)
from apps.survey_analysis.lca.stepmix_model import StepMixLCA

LCA_REGISTRY.update({
    "stepmix": StepMixLCA,
})

__all__ = [
    "LCAEngine",
    "LCAEngineError",
    "LCA_REGISTRY",
    "get_lca_engine",
    "StepMixLCA",
]
