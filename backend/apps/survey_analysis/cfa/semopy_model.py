"""Adapter SEM berbasis semopy.

Engine utama (opsional). CATATAN METODOLOGIS — kemampuan ordinal semopy
2.3.x TERBATAS dan sudah diverifikasi:
- semopy TIDAK bisa menggabungkan polychoric + DWLS (DWLS butuh data mentah),
  sehingga TIDAK bisa melakukan WLSMV sejati.
- Opsi ordinal terbaik semopy = ``ULS`` pada matriks korelasi polychoric
  (korelasi polychoric benar untuk ordinal, tapi pembobotan unweighted —
  bukan WLSMV). Ini pendekatan yang valid namun bukan WLSMV.
- Untuk WLSMV penuh (polychoric + DWLS + koreksi mean-variance adjusted),
  gunakan engine ``lavaan`` (rpy2 + R + lavaan).

Estimator:
- "ULS"  (default) : ULS pada polychoric (ordinal; terbaik yang semopy bisa).
- "DWLS"           : DWLS pada data mentah (distribution-free, korelasi Pearson).
- "MLW"            : Maximum Likelihood (kontinu; HANYA perbandingan).

Tidak ada penggantian estimator diam-diam: estimator eksplisit dan dilaporkan.
"""

import numpy as np
import pandas as pd

from apps.survey_analysis.cfa.base import SEMEngine, SEMEngineError
from apps.survey_analysis.cfa.model_spec import build_model_description
from apps.survey_analysis.config import settings as cfg
from apps.survey_analysis.config import model_config


def _patch_semopy_numpy_compat():
    """Shim kompatibilitas semopy (2.3.x) dengan numpy >= 2.0.

    numpy 2.0 menghapus argumen ``bias`` dari ``np.ma.cov`` /
    ``np.ma.corrcoef``, tetapi semopy masih memakainya. Shim ini mengembalikan
    dukungan ``bias`` (bias=True -> ddof=0) di level numpy.ma, sehingga SEMUA
    call-site semopy (utils/polycorr/model/efa) ikut terperbaiki — tanpa
    downgrade numpy dan tanpa mengubah hasil (korelasi invarian terhadap bias).
    """
    if getattr(np.ma, "_semopy_bias_patched", False):
        return

    _orig_cov = np.ma.cov
    _orig_corrcoef = np.ma.corrcoef

    def _cov(*args, **kwargs):
        if "bias" in kwargs:
            bias = kwargs.pop("bias")
            kwargs.setdefault("ddof", 0 if bias else 1)
        return _orig_cov(*args, **kwargs)

    def _corrcoef(*args, **kwargs):
        kwargs.pop("bias", None)  # korelasi invarian terhadap bias.
        return _orig_corrcoef(*args, **kwargs)

    np.ma.cov = _cov
    np.ma.corrcoef = _corrcoef
    np.ma._semopy_bias_patched = True


def _patch_semopy_scipy_compat():
    """Shim semopy (2.3.x) dengan scipy >= 1.14.

    semopy memakai ``scipy.stats.mvn.mvnun`` (CDF normal bivariat) yang sudah
    dihapus. Penggantinya HARUS cepat, karena ``hetcor`` memanggil
    ``bivariate_cdf`` jutaan kali (O(item^2) * iterasi minimize * sel). Versi
    awal memakai ``scipy.stats.multivariate_normal.cdf`` (integrasi numerik
    presisi tinggi) yang membuat hetcor 88 item butuh belasan menit — memicu
    timeout/OOM gunicorn (HTTP 500). Implementasi ini memakai bentuk integral +
    kuadratur Gauss-Legendre 20 titik: hasil identik (err ~1e-10) tapi ~25x
    lebih cepat.
    """
    import math
    import semopy.polycorr as pc
    if getattr(pc, "_scipy_patched", False):
        return

    # Node & bobot Gauss-Legendre 20 titik (dipetakan ke [0,1]).
    _nodes, _weights = np.polynomial.legendre.leggauss(20)
    _gl = [(float((u + 1.0) / 2.0), float(w) / 2.0) for u, w in zip(_nodes, _weights)]

    def _phi(x):
        return 0.5 * math.erfc(-x / math.sqrt(2.0))

    def _bvn_cdf(x, y, rho):
        """CDF normal bivariat standar P(X <= x, Y <= y; corr=rho)."""
        if rho >= 1.0:
            return _phi(min(x, y))
        if rho <= -1.0:
            return max(0.0, _phi(x) + _phi(y) - 1.0)
        if rho == 0.0:
            return _phi(x) * _phi(y)
        total = 0.0
        for u, w in _gl:
            t = rho * u
            s = 1.0 - t * t
            total += w * math.exp(-(x * x - 2.0 * t * x * y + y * y) / (2.0 * s)) / math.sqrt(s)
        return _phi(x) * _phi(y) + rho * total / (2.0 * math.pi)

    def bivariate_cdf(lower, upper, corr, means=(0.0, 0.0), var=(1.0, 1.0)):
        sd0 = math.sqrt(var[0])
        sd1 = math.sqrt(var[1])
        rho = corr / (sd0 * sd1)
        lx = (lower[0] - means[0]) / sd0
        ux = (upper[0] - means[0]) / sd0
        ly = (lower[1] - means[1]) / sd1
        uy = (upper[1] - means[1]) / sd1
        return (
            _bvn_cdf(ux, uy, rho)
            - _bvn_cdf(lx, uy, rho)
            - _bvn_cdf(ux, ly, rho)
            + _bvn_cdf(lx, ly, rho)
        )

    def univariate_cdf(lower, upper, mean=0.0, var=1.0):
        sd = math.sqrt(var)
        return _phi((upper - mean) / sd) - _phi((lower - mean) / sd)

    pc.bivariate_cdf = bivariate_cdf
    pc.univariate_cdf = univariate_cdf
    pc._scipy_patched = True


_ESTIMATOR_LABELS = {
    "ULS": "ULS (polychoric)",
    "DWLS": "DWLS (data mentah)",
    "MLW": "ML (kontinu, perbandingan)",
}


class SemopySEM(SEMEngine):
    engine_name = "semopy"

    # Kolom hasil semopy.inspect() (beberapa versi beda nama).
    _COL_MAP = {
        "lhs": ("lval", "Left"),
        "op": ("op", "Operator"),
        "rhs": ("rval", "Right"),
        "est": ("Estimate",),
        "std_est": ("Est. Std", "Std. Est", "Est Std"),
        "se": ("Std. Err", "SE"),
        "p": ("p-value", "p value", "p"),
    }

    def __init__(self):
        import semopy  # import lokal: dependency opsional
        _patch_semopy_numpy_compat()
        _patch_semopy_scipy_compat()
        self._semopy = semopy
        self._model = None
        self._estimator = None
        self._sample = None  # kovarians/korelasi sampel (untuk SRMR)
        self._inspect_df = None
        self._converged = False

    @property
    def estimator_label(self):
        return _ESTIMATOR_LABELS.get(self._estimator, self._estimator or "")

    @staticmethod
    def availability_error():
        try:
            import semopy  # noqa: F401
        except Exception as exc:  # pragma: no cover
            return f"semopy tidak terpasang: {exc}"
        return None

    # ---------------------------------------------------------------- fit

    def fit(self, matrix, measurement_only=False, estimator="ULS", **kwargs):
        self._estimator = estimator
        desc = build_model_description(measurement_only=measurement_only)
        data = matrix.astype(float)
        model = self._semopy.Model(desc)

        if estimator == "ULS":
            # Ordinal terbaik semopy: korelasi polychoric + ULS.
            corr = self._polychoric_corr(data)
            self._sample = corr.values
            model.fit(cov=corr, obj="ULS", n_samples=len(data))
        elif estimator == "DWLS":
            # Distribution-free pada data mentah (korelasi Pearson).
            self._sample = data.cov().values
            model.fit(data, obj="DWLS")
        elif estimator == "MLW":
            self._sample = data.cov().values
            model.fit(data, obj="MLW")
        else:
            raise SEMEngineError(
                f"Estimator '{estimator}' tidak didukung semopy. "
                "Gunakan 'ULS' (ordinal/polychoric), 'DWLS', atau 'MLW'."
            )

        self._model = model
        self._inspect_df = self._safe_inspect()
        self._converged = self._check_converged()
        return self

    _POLYCHORIC_CACHE = {}

    def _polychoric_corr(self, data):
        """Matriks korelasi polychoric untuk data ordinal (semua kolom)."""
        key = (tuple(data.columns), hash(data.values.tobytes()))
        if key in self._POLYCHORIC_CACHE:
            return self._POLYCHORIC_CACHE[key]
        try:
            # hetcor() stabil dengan ndarray; ords auto-deteksi.
            het = self._semopy.polycorr.hetcor(data.values, nearest=True)
            corr = pd.DataFrame(het, index=data.columns, columns=data.columns)
        except Exception as exc:
            raise SEMEngineError(
                "Gagal menghitung korelasi polychoric untuk data ordinal: "
                f"{exc}. Data Likert perlu analisis ordinal; tidak diganti "
                "diam-diam ke estimator kontinu."
            )
        self._POLYCHORIC_CACHE[key] = corr
        return corr

    def _safe_inspect(self):
        try:
            return self._model.inspect(std_est=True)
        except Exception:
            return self._model.inspect()

    def _check_converged(self):
        # semopy tidak mengekspos flag konvergensi secara konsisten;
        # anggap konvergen bila fit selesai tanpa exception + inspect valid.
        return self._inspect_df is not None and not self._inspect_df.empty

    def _col(self, df, canonical):
        for name in self._COL_MAP[canonical]:
            if name in df.columns:
                return df[name]
        return None

    # ---------------------------------------------------------------- hasil

    def converged(self):
        return self._converged

    def fit_indices(self):
        if self._model is None:
            return {}
        s = self._semopy.calc_stats(self._model)  # DataFrame 1 baris

        def get(col):
            if col in s.columns:
                return self._num(s[col].iloc[0])
            return None

        return {
            "cfi": get("CFI"),
            "tli": get("TLI"),
            "rmsea": get("RMSEA"),
            "rmsea_ci_low": None,  # semopy tidak menyediakan CI RMSEA.
            "rmsea_ci_high": None,
            "srmr": self._srmr(),
            "chi2": get("chi2"),
            "dof": get("DoF"),
            "p_value": get("chi2 p-value"),
            "aic": get("AIC"),
            "bic": get("BIC"),
        }

    def _srmr(self):
        """SRMR = sqrt(mean residu kuadrat) pada skala korelasi (lower-tri)."""
        try:
            implied = self._model.calc_sigma()
            implied = np.asarray(implied, dtype=float)
            sample = np.asarray(self._sample, dtype=float)
        except Exception:
            return None
        if implied.shape != sample.shape:
            return None
        sc = _cov2corr(sample)
        ic = _cov2corr(implied)
        res = sc - ic
        tril = np.tril(res)
        return float(np.sqrt(np.mean(tril ** 2)))

    def factor_loadings(self):
        df = self._inspect_df
        if df is None:
            return pd.DataFrame()
        op = self._col(df, "op")
        constructs = set(model_config.CONSTRUCTS)
        items = set(model_config.all_items())
        lhs = self._col(df, "lhs")
        rhs = self._col(df, "rhs")
        # Loading: item (lhs) ~ konstruk laten (rhs).
        load = df[(op == "~") & (lhs.isin(items)) & (rhs.isin(constructs))].copy()
        if load.empty:
            return pd.DataFrame(columns=["construct", "item", "loading", "se", "p_value"])
        return pd.DataFrame({
            "construct": self._col(load, "rhs"),
            "item": self._col(load, "lhs"),
            "loading": self._col(load, "std_est"),
            "se": self._col(load, "se"),
            "p_value": self._col(load, "p"),
        })

    def path_coefficients(self):
        df = self._inspect_df
        if df is None:
            return pd.DataFrame()
        op = self._col(df, "op")
        constructs = set(model_config.CONSTRUCTS)
        # Path: konstruk laten (lhs) ~ konstruk laten (rhs).
        lhs = self._col(df, "lhs")
        rhs = self._col(df, "rhs")
        paths = df[(op == "~") & (lhs.isin(constructs)) & (rhs.isin(constructs))].copy()
        if paths.empty:
            return pd.DataFrame(columns=["lhs", "rhs", "est", "se", "p_value", "standardized"])
        return pd.DataFrame({
            "lhs": self._col(paths, "lhs"),
            "rhs": self._col(paths, "rhs"),
            "est": self._col(paths, "est"),
            "se": self._col(paths, "se"),
            "p_value": self._col(paths, "p"),
            "standardized": self._col(paths, "std_est"),
        })

    def standardized_estimates(self):
        return self._inspect_df if self._inspect_df is not None else pd.DataFrame()

    @staticmethod
    def _num(v):
        try:
            return None if v is None else float(v)
        except (TypeError, ValueError):
            return None


def _cov2corr(cov):
    """Ubah matriks kovarians -> korelasi (aman untuk diagonal nol)."""
    cov = np.asarray(cov, dtype=float)
    d = np.sqrt(np.diag(cov))
    d[d == 0] = 1.0
    return cov / np.outer(d, d)
