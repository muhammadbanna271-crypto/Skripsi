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


def select_n_clusters(X, max_k=6, random_state=42):
    """Pilih jumlah cluster (k) K-Means secara data-driven (silhouette).

    Menghitung silhouette score + inertia untuk k = 2..max_k pada data yang
    sudah di-standardize, lalu memilih k dengan silhouette tertinggi. Ini
    menggantikan hard-code ``k=3`` supaya jumlah cluster mengikuti data.

    Return dict:
      {"selected": int, "curve": [{"k", "silhouette", "inertia"}, ...]}

    ``curve`` disimpan untuk transparansi (dashboard bisa menampilkan kenapa
    k tertentu terpilih), bukan sekadar angka.
    """
    X = np.asarray(X, dtype=float)
    n = X.shape[0]
    if n < 3:
        return {"selected": 1, "curve": []}

    upper = min(max_k, n - 1)  # k harus < n.
    if upper < 2:
        return {"selected": 1, "curve": []}

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    curve = []
    best_k, best_score = 2, -1.0
    for k in range(2, upper + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=random_state)
        labels = km.fit_predict(Xs)
        score = float(silhouette_score(Xs, labels))
        if np.isnan(score):
            score = -1.0  # cluster berisi <2 sampel -> silhouette tak terdefinisi.
        curve.append({
            "k": k,
            "silhouette": round(score, 4),
            "inertia": round(float(km.inertia_), 2),
        })
        if score > best_score:
            best_k, best_score = k, score

    return {"selected": best_k, "curve": curve}
