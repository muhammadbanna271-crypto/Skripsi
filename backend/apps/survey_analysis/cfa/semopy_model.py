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

import math

import numpy as np
import pandas as pd

from apps.survey_analysis.cfa.base import SEMEngine, SEMEngineError
from apps.survey_analysis.cfa.model_spec import build_model_description
from apps.survey_analysis.config import settings as cfg
from apps.survey_analysis.config import model_config


# ---------------------------------------------------------------------------
# Korelasi polychoric self-contained.
#
# semopy.polycorr.hetcor() memakai ``scipy.stats.mvn.mvnun`` yang SUDAH DIHAPUS
# sejak scipy >= 1.14 (error: "mvn has no attribute mvnun"). Monkey-patch shim
# (lihat ``_patch_semopy_scipy_compat``) terbukti tidak andal di production,
# jadi di sini bivariate normal CDF + polychoric correlation dihitung langsung:
# kuadratur Gauss-Legendre 20 titik (hasil identik dgn mvn.mvnun, err ~1e-10,
# ~25x lebih cepat) dan estimasi korelasi per-pasang via ``minimize_scalar``.
# ---------------------------------------------------------------------------

_GL_NODES, _GL_WEIGHTS = np.polynomial.legendre.leggauss(20)
# Node & bobot Gauss-Legendre dipetakan dari [-1, 1] ke [0, 1] (domain 0..rho).
_GL = [(float((u + 1.0) / 2.0), float(w) / 2.0)
       for u, w in zip(_GL_NODES, _GL_WEIGHTS)]


def _phi(x):
    """CDF normal standar."""
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
    for u, w in _GL:
        t = rho * u
        s = 1.0 - t * t
        total += w * math.exp(-(x * x - 2.0 * t * x * y + y * y) / (2.0 * s)) / math.sqrt(s)
    return _phi(x) * _phi(y) + rho * total / (2.0 * math.pi)


def _polychoric_corr_matrix(data):
    """Matriks korelasi polychoric untuk data ordinal (semua kolom).

    Reimplementasi ``semopy.hetcor()`` untuk kasus semua-ordinal: threshold per
    item via ``norm.ppf`` dari proporsi kumulatif, lalu korelasi polychoric
    per-pasang via ``minimize_scalar`` atas negative log-likelihood (bivariate
    CDF = Gauss-Legendre lokal). Hasil dikoreksi ke nearest positive-definite
    (threshold 0.05, sama seperti ``hetcor(nearest=True)``).
    """
    from scipy.optimize import minimize_scalar
    from scipy.stats import norm
    from statsmodels.stats.correlation_tools import corr_nearest

    cols = list(data.columns)
    X = data.astype(float).values
    n_cols = X.shape[1]

    def estimate_intervals(x):
        x_f = x[~np.isnan(x)]
        u, counts = np.unique(x_f, return_counts=True)
        sz = len(x_f)
        cum = np.cumsum(counts[:-1])
        thresholds = [-10.0] + [float(norm.ppf(n / sz)) for n in cum] + [10.0]
        inds = np.searchsorted(u, x).astype(float) + 1.0
        inds[np.isnan(x)] = np.nan
        return thresholds, inds

    intervals = [estimate_intervals(X[:, j]) for j in range(n_cols)]
    R = np.eye(n_cols)
    for a in range(n_cols):
        x_ints, x_inds = intervals[a]
        p = len(x_ints) - 1
        for b in range(a + 1, n_cols):
            y_ints, y_inds = intervals[b]
            m = len(y_ints) - 1
            n = np.zeros((p, m))
            for ia, ib in zip(x_inds, y_inds):
                if not (np.isnan(ia) or np.isnan(ib)):
                    n[int(ia) - 1, int(ib) - 1] += 1

            def neg_loglik(r):
                s = 0.0
                for i in range(p):
                    for j in range(m):
                        if n[i, j] == 0:
                            continue
                        prob = (
                            _bvn_cdf(x_ints[i + 1], y_ints[j + 1], r)
                            - _bvn_cdf(x_ints[i], y_ints[j + 1], r)
                            - _bvn_cdf(x_ints[i + 1], y_ints[j], r)
                            + _bvn_cdf(x_ints[i], y_ints[j], r)
                        )
                        if prob <= 0.0:
                            prob = 1e-12
                        s += math.log(prob) * n[i, j]
                return -s

            r = float(minimize_scalar(neg_loglik, bounds=(-1.0, 1.0),
                                      method="bounded").x)
            if not np.isfinite(r):
                r = 0.0
            R[a, b] = R[b, a] = r

    R = corr_nearest(R, threshold=0.05)
    return pd.DataFrame(R, index=cols, columns=cols)


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
            corr = _polychoric_corr_matrix(data)
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

        # SRMR valid untuk semua estimator (residual berbasis skala korelasi).
        indices = {
            "srmr": self._srmr(),
            "chi2": get("chi2"),
            "dof": get("DoF"),
            "aic": get("AIC"),
            "bic": get("BIC"),
        }

        if self._estimator == "ULS":
            # ULS (unweighted least squares) TIDAK punya distribusi chi-square
            # yang diketahui, sehingga CFI/TLI/RMSEA/p-value — yang dikalibrasi
            # untuk ML/WLSMV (Hu & Bentler, 1999) — TIDAK valid. Melaporkan/
            # menggating indeks tsb di sini adalah category error. Untuk
            # CFI/TLI/RMSEA yang valid, gunakan engine 'lavaan' (WLSMV).
            indices.update({
                "cfi": None,
                "tli": None,
                "rmsea": None,
                "rmsea_ci_low": None,
                "rmsea_ci_high": None,
                "p_value": None,
            })
        else:
            indices.update({
                "cfi": get("CFI"),
                "tli": get("TLI"),
                "rmsea": get("RMSEA"),
                "rmsea_ci_low": None,  # semopy tidak menyediakan CI RMSEA.
                "rmsea_ci_high": None,
                "p_value": get("chi2 p-value"),
            })
        return indices

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
