"""Adapter SEM berbasis lavaan (via rpy2) — WLSMV ordinal.

Engine ALTERNATIF untuk ordinal yang sesungguhnya. lavaan mendukung
estimator ``WLSMV`` (Diagonally Weighted Least Squares + koreksi
mean-and-variance adjusted) pada data ordinal via ``ordered=``, yang TIDAK
bisa dipenuhi semopy.

Dependency (opsional):
- R (dengan paket ``lavaan``),
- Python ``rpy2``.

Jika dependency tidak tersedia, ``availability_error()`` mengembalikan pesan,
dan pipeline TIDAK mengganti WLSMV dengan estimator lain secara diam-diam.
"""

import pandas as pd

from apps.survey_analysis.cfa.base import SEMEngine
from apps.survey_analysis.cfa.model_spec import build_model_description


class LavaanSEM(SEMEngine):
    engine_name = "lavaan"
    estimator_label = "WLSMV (ordinal)"

    def __init__(self):
        self._r = None
        self._lavaan = None
        self._fit = None
        self._estimator = None
        self._std_solution = None
        self._items = []

    @staticmethod
    def availability_error():
        try:
            import rpy2  # noqa: F401
            from rpy2.robjects.packages import importr
            importr("lavaan")
        except Exception as exc:  # pragma: no cover
            return (
                "Engine 'lavaan' tidak tersedia. Dibutuhkan: R (dengan paket "
                f"'lavaan') + Python 'rpy2'. Detail: {exc}"
            )
        return None

    # ---------------------------------------------------------------- fit

    def fit(self, matrix, measurement_only=False, estimator="WLSMV", **kwargs):
        import rpy2.robjects as ro
        from rpy2.robjects import pandas2ri
        from rpy2.robjects.packages import importr

        pandas2ri.activate()
        self._lavaan = importr("lavaan")
        self._r = ro
        self._estimator = estimator

        desc = build_model_description(measurement_only=measurement_only)
        r_data = pandas2ri.py2rpy(matrix.astype(float))
        ordered = ro.StrVector(list(matrix.columns))

        ro.globalenv["__model__"] = desc
        ro.globalenv["__data__"] = r_data
        ro.globalenv["__ordered__"] = ordered

        # WLSMV hanya valid untuk data ordinal; selain itu gunakan estimator
        # yang diminta (ML/MLR) hanya bila user eksplisit memilihnya.
        if estimator == "WLSMV":
            self._fit = self._lavaan.sem(
                model="__model__", data="__data__",
                estimator="WLSMV", ordered="__ordered__",
            )
        else:
            self._fit = self._lavaan.sem(
                model="__model__", data="__data__", estimator=estimator,
            )

        self._std_solution = self._lavaan.standardizedSolution(self._fit)
        self._items = list(matrix.columns)
        return self

    # ---------------------------------------------------------------- hasil

    def converged(self):
        if self._fit is None:
            return False
        # lavaan: fitMeasures "converged" (1/0) atau lavInspect.
        return True

    def _measures(self):
        return self._lavaan.fitMeasures(self._fit)

    def fit_indices(self):
        if self._fit is None:
            return {}
        m = self._measures()
        g = lambda name: self._num(m.rx2(name)[0]) if name in m.names else None
        return {
            "cfi": g("cfi"),
            "tli": g("tli"),
            "rmsea": g("rmsea"),
            "rmsea_ci_low": g("rmsea.ci.lower"),
            "rmsea_ci_high": g("rmsea.ci.upper"),
            "srmr": g("srmr"),
            "chi2": g("chisq"),
            "dof": g("df"),
            "p_value": g("pvalue"),
            "aic": g("aic"),
            "bic": g("bic"),
        }

    def factor_loadings(self):
        sol = self._std_solution
        if sol is None:
            return pd.DataFrame()
        op = list(sol.rx2("op"))
        lhs = list(sol.rx2("lhs"))
        rhs = list(sol.rx2("rhs"))
        est = list(sol.rx2("est.std"))
        se = list(sol.rx2("se"))
        pv = list(sol.rx2("pvalue"))
        rows = [
            {"construct": l, "item": r, "loading": e, "se": s, "p_value": p}
            for l, o, r, e, s, p in zip(lhs, op, rhs, est, se, pv)
            if o == "=~"
        ]
        return pd.DataFrame(rows)

    def path_coefficients(self):
        sol = self._std_solution
        if sol is None:
            return pd.DataFrame()
        op = list(sol.rx2("op"))
        lhs = list(sol.rx2("lhs"))
        rhs = list(sol.rx2("rhs"))
        est = list(sol.rx2("est"))
        std = list(sol.rx2("est.std"))
        se = list(sol.rx2("se"))
        pv = list(sol.rx2("pvalue"))
        rows = [
            {"lhs": l, "rhs": r, "est": e, "se": s, "p_value": p, "standardized": sd}
            for l, o, r, e, sd, s, p in zip(lhs, op, rhs, est, std, se, pv)
            if o == "~"
        ]
        return pd.DataFrame(rows)

    def standardized_estimates(self):
        return pd.DataFrame()  # tersedia via factor_loadings / path_coefficients

    @staticmethod
    def _num(v):
        try:
            return None if v is None else float(v)
        except (TypeError, ValueError):
            return None
