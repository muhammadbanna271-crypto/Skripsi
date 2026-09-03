"""Paket ML surrogate: registry model."""

from apps.survey_analysis.ml.base import MLModel, MLEngineError, ML_REGISTRY, get_ml_model
from apps.survey_analysis.ml.xgboost_model import XGBoostModel
from apps.survey_analysis.ml.random_forest import RandomForestModel

ML_REGISTRY.update({
    "xgboost": XGBoostModel,
    "random_forest": RandomForestModel,
})

__all__ = [
    "MLModel",
    "MLEngineError",
    "ML_REGISTRY",
    "get_ml_model",
    "XGBoostModel",
    "RandomForestModel",
]
