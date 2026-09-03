"""Model Random Forest (comparison model).

Memakai preprocessing & split yang SAMA dengan XGBoost (diatur di runner),
bukan di model — sehingga perbandingan adil.
"""

from apps.survey_analysis.ml.base import MLModel


class RandomForestModel(MLModel):
    model_name = "random_forest"

    def __init__(self):
        self._model = None
        self.best_params_ = None

    @staticmethod
    def availability_error():
        try:
            import sklearn.ensemble  # noqa: F401
        except Exception as exc:  # pragma: no cover
            return f"scikit-learn tidak terpasang: {exc}"
        return None

    def fit(self, X_train, y_train, cv_folds=5, random_state=42, **kwargs):
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import GridSearchCV

        clf = RandomForestClassifier(random_state=random_state, n_jobs=-1)
        grid = GridSearchCV(
            clf,
            {"n_estimators": [100, 200], "max_depth": [None, 8, 12]},
            scoring="accuracy",
            cv=cv_folds,
            n_jobs=-1,
            verbose=0,
        )
        grid.fit(X_train, y_train)
        self._model = grid.best_estimator_
        self.best_params_ = grid.best_params_
        return self

    def predict(self, X):
        return self._model.predict(X)

    def predict_proba(self, X):
        return self._model.predict_proba(X)
