"""Model XGBoost (surrogate ML utama).

Lightweight hyperparameter tuning via 5-fold stratified GridSearchCV pada
grid kecil (bukan tuning berlebihan). Seluruh konfigurasi tuning dicatat
(disimpan di atribut ``best_params_`` + ``cv_results_``).
"""

from apps.survey_analysis.ml.base import MLModel


class XGBoostModel(MLModel):
    model_name = "xgboost"

    PARAM_GRID = {
        "n_estimators": [100, 200],
        "max_depth": [3, 5],
        "learning_rate": [0.1],
        "subsample": [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0],
    }

    def __init__(self):
        self._model = None
        self.best_params_ = None
        self.cv_results_ = None

    @staticmethod
    def availability_error():
        try:
            import xgboost  # noqa: F401
        except Exception as exc:  # pragma: no cover
            return f"xgboost tidak terpasang: {exc}"
        return None

    def fit(self, X_train, y_train, cv_folds=5, random_state=42, **kwargs):
        import xgboost as xgb
        from sklearn.model_selection import GridSearchCV

        clf = xgb.XGBClassifier(
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=random_state,
            n_jobs=1,
        )
        grid = GridSearchCV(
            clf,
            self.PARAM_GRID,
            scoring="accuracy",
            cv=cv_folds,
            n_jobs=-1,
            verbose=0,
        )
        grid.fit(X_train, y_train)
        self._model = grid.best_estimator_
        self.best_params_ = grid.best_params_
        self.cv_results_ = grid.cv_results_
        return self

    def predict(self, X):
        return self._model.predict(X)

    def predict_proba(self, X):
        return self._model.predict_proba(X)
