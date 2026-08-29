import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from apps.analytics.ml.storage import (
    load_object,
    save_object,
)


SCALER_FILENAME = "village_scaler.joblib"

KMEANS_FILENAME = "village_kmeans.joblib"


class KMeansClusterModel:
    """
    Wrapper K-Means untuk clustering desa.

    - Unsupervised: TIDAK ada train/test split.
    - Model (scaler + kmeans) disimpan ke disk (joblib) supaya
      prediksi data baru tidak perlu fit ulang, cukup .predict().
    """

    def __init__(self, n_clusters=3, random_state=42):

        self.n_clusters = n_clusters

        self.random_state = random_state

        self.scaler = None

        self.model = None

    # =========================================================
    # TRAINING (dipanggil sekali atas seluruh data historis,
    # atau saat admin klik "Retrain Model")
    # =========================================================

    def fit(self, X):
        """
        X: matrix [n_desa x n_indikator], seluruh data historis.

        Return dict berisi label per baris & metrik evaluasi.
        """

        X = np.array(X, dtype=float)

        self.scaler = StandardScaler()

        X_scaled = self.scaler.fit_transform(X)

        self.model = KMeans(
            n_clusters=self.n_clusters,
            random_state=self.random_state,
            n_init=10,
        )

        labels = self.model.fit_predict(X_scaled)

        score = None

        if len(set(labels)) > 1 and len(X) > self.n_clusters:

            score = float(
                silhouette_score(X_scaled, labels)
            )

        return {

            "labels": labels.tolist(),

            "centroids": self.model.cluster_centers_.tolist(),

            "silhouette_score": score,

            "inertia": float(self.model.inertia_),

        }

    # =========================================================
    # PREDIKSI DESA BARU (tidak fit ulang, hanya .predict())
    # =========================================================

    def predict(self, X):

        if self.model is None or self.scaler is None:

            raise ValueError(
                "Model belum di-load / belum di-training. "
                "Jalankan training terlebih dahulu."
            )

        X = np.array(X, dtype=float)

        X_scaled = self.scaler.transform(X)

        labels = self.model.predict(X_scaled)

        return labels.tolist()

    # =========================================================
    # PERSISTENCE
    # =========================================================

    def save(self):

        save_object(self.scaler, SCALER_FILENAME)

        save_object(self.model, KMEANS_FILENAME)

    @classmethod
    def load(cls):
        """
        Load model yang sudah pernah di-training dari disk.
        Return None kalau belum pernah ada training.
        """

        scaler = load_object(SCALER_FILENAME)

        model = load_object(KMEANS_FILENAME)

        if scaler is None or model is None:
            return None

        instance = cls(n_clusters=model.n_clusters)

        instance.scaler = scaler

        instance.model = model

        return instance

    @classmethod
    def is_trained(cls):

        return (
            load_object(SCALER_FILENAME) is not None
            and load_object(KMEANS_FILENAME) is not None
        )
