"""Adapter LCA berbasis StepMix (engine utama LCA).

StepMix memodelkan item Likert sebagai kategorikal (measurement='categorical'),
sehingga class response probabilities diestimasi langsung dari raw items —
bukan dari factor scores / skor kontinu.
"""

import pandas as pd

from apps.survey_analysis.lca.base import LCAEngine


class StepMixLCA(LCAEngine):
    engine_name = "stepmix"

    def __init__(self):
        self._model = None
        self.n_classes = None
        self.random_state = None
        self._data = None

    @staticmethod
    def availability_error():
        try:
            import stepmix  # noqa: F401
        except Exception as exc:  # pragma: no cover
            return f"stepmix tidak terpasang: {exc}"
        return None

    def fit(self, matrix, n_classes, random_state, **kwargs):
        from stepmix import StepMix
        self.n_classes = n_classes
        self.random_state = random_state
        self._data = matrix.astype(float)
        self._model = StepMix(
            n_components=n_classes,
            measurement="categorical",
            random_state=random_state,
            verbose=0,
            progress_bar=0,
        )
        self._model.fit(self._data.values)
        return self

    def predict_proba(self, matrix):
        return pd.DataFrame(
            self._model.predict_proba(matrix.astype(float).values),
            index=matrix.index,
        )

    def predict_class(self, matrix):
        return pd.Series(
            self._model.predict_class(matrix.astype(float).values),
            index=matrix.index,
            name="class",
        )

    def bic(self, matrix):
        return float(self._model.bic(matrix.astype(float).values))

    def aic(self, matrix):
        return float(self._model.aic(matrix.astype(float).values))

    def log_likelihood(self, matrix):
        return float(self._model.score(matrix.astype(float).values))

    def relative_entropy(self):
        return float(self._model.relative_entropy(self._data.values))

    def item_probabilities(self):
        """Probabilitas respons item per kelas (long format).

        stepmix 3.x mengembalikan get_mm_df() sebagai matriks dengan
        MultiIndex ('categorical','pis','feature_<i>_<cat>') dan kolom = kelas.
        Di sini diubah ke long DataFrame [class, item, category, probability].
        """
        mm = self._model.get_mm_df()
        item_names = list(self._data.columns)
        rows = []
        for idx in mm.index:
            # idx = ('categorical', 'pis', 'feature_<item>_<category>')
            feature_cat = str(idx[-1])
            parts = feature_cat.split("_")  # ['feature', item_idx, category]
            feat_idx = int(parts[1])
            category = int(parts[2])
            item = item_names[feat_idx]
            for cls in mm.columns:
                rows.append({
                    "class": int(cls),
                    "item": item,
                    "category": category,
                    "probability": float(mm.loc[idx, cls]),
                })
        return pd.DataFrame(rows)
