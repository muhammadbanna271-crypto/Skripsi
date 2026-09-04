"""Service dashboard: cache + staleness + load hasil pipeline survei.

Menyediakan data SEM/LCA/SHAP untuk ML Dashboard (apps.analytics) tanpa perlu
menjalankan pipeline berat setiap kali halaman dibuka.

Pola "train-or-cache" mirip ClusteringService.ensure_trained(), tapi cache-nya
berbasis file (outputs/reports/cache_state.json) sehingga tidak perlu migrasi DB:

- Belum ada hasil / data berubah -> jalankan (retrain) dulu.
- Sudah ada & tidak stale -> cukup baca file output (ringan).
"""

import hashlib
import json
import os
from datetime import datetime

import pandas as pd

from apps.analytics.colors import color_for_index
from apps.survey_analysis.config import settings as cfg


def _r(v, nd=3):
    """Bulatkan float untuk tampilan; kembalikan None untuk None/NaN."""
    if v is None:
        return None
    try:
        f = float(v)
        if f != f:  # NaN
            return None
        return round(f, nd)
    except (TypeError, ValueError):
        return v


class SurveyAnalysisDashboard:

    CACHE_FILE = cfg.OUTPUT_DIR / "reports" / "cache_state.json"
    STATE_FILE = cfg.OUTPUT_DIR / "reports" / "pipeline_state.json"
    RUNNING_FILE = cfg.OUTPUT_DIR / "reports" / "running.json"

    # =========================================================
    # SIGNATURE (deteksi perubahan data, murah)
    # =========================================================

    @staticmethod
    def signature():
        """Hash murah dari data sumber (tanpa memuat semua baris)."""
        from apps.response.models import Response
        from apps.master.models import Questionnaire

        likert = dict(
            questionnaire__answer_type="likert",
            answer_integer__isnull=False,
        )
        n = Response.objects.filter(**likert).count()
        last_resp = (
            Response.objects.filter(**likert)
            .order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )
        items = list(
            Questionnaire.objects.filter(
                answer_type="likert",
                is_active=True,
            )
            .order_by("indicator__code", "question_order")
            .values_list("indicator__code", "question", "question_order")
        )
        raw = f"{n}|{last_resp}|{items}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    # =========================================================
    # STALE / HAS-RESULTS
    # =========================================================

    @classmethod
    def _read_cache(cls):
        if not cls.CACHE_FILE.exists():
            return None
        try:
            return json.loads(cls.CACHE_FILE.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None

    @classmethod
    def _write_cache(cls, signature):
        cls.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "signature": signature,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        cls.CACHE_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def is_stale(cls):
        cache = cls._read_cache()
        if cache is None:
            return True
        return cache.get("signature") != cls.signature()

    @classmethod
    def has_results(cls):
        return cls.STATE_FILE.exists()

    # =========================================================
    # BACKGROUND RUN (marker "sedang berjalan", anti-double-run)
    # =========================================================

    @classmethod
    def is_running(cls):
        """True bila pipeline sedang berjalan di background.

        Marker ditulis oleh ``start_background`` dan dihapus oleh management
        command saat selesai. Bila marker menyisakan PID yang sudah mati
        (proses OOM/kill tanpa sempat membersihkan), marker dianggap stale
        dan dibersihkan di sini.
        """
        if not cls.RUNNING_FILE.exists():
            return False
        try:
            data = json.loads(cls.RUNNING_FILE.read_text(encoding="utf-8"))
            pid = data.get("pid")
        except (ValueError, OSError):
            # Marker korup/kosong (mis. crash tepat setelah claim) -> stale.
            cls.clear_running()
            return False
        if pid is None:
            return True
        try:
            os.kill(int(pid), 0)  # signal 0 = cek liveness (POSIX).
        except ProcessLookupError:
            cls.clear_running()
            return False
        except (PermissionError, ValueError, OSError):
            return True
        return True

    @classmethod
    def clear_running(cls):
        try:
            cls.RUNNING_FILE.unlink()
        except OSError:
            pass

    @classmethod
    def start_background(cls):
        """Jalankan pipeline lewat ``manage.py run_survey_pipeline`` sebagai
        subprocess terpisah (detached), sehingga request web tidak memblokir
        dan tidak terkena timeout gunicorn. Return True bila berhasil memulai;
        False bila sudah ada run yang berjalan."""
        import subprocess
        import sys
        import threading

        from django.conf import settings

        cls.RUNNING_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Klaim slot "running" secara atomik (cegah double-run dari double-click).
        try:
            fd = os.open(
                str(cls.RUNNING_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY
            )
            os.close(fd)
        except FileExistsError:
            return False

        manage = settings.BASE_DIR / "manage.py"
        log_path = cfg.OUTPUT_DIR / "reports" / "pipeline_run.log"
        popen_kwargs = {}
        if os.name == "posix":
            # Lepas dari process group gunicorn supaya worker yang di-recycle
            # tidak ikut mematikan pipeline.
            popen_kwargs["start_new_session"] = True

        try:
            with open(log_path, "a", encoding="utf-8") as logf:
                proc = subprocess.Popen(
                    [sys.executable, str(manage), "run_survey_pipeline"],
                    cwd=str(settings.BASE_DIR),
                    stdout=logf,
                    stderr=subprocess.STDOUT,
                    **popen_kwargs,
                )
        except Exception:
            cls.clear_running()
            raise

        # Reap child di thread terpisah supaya proses yang selesai/terkill
        # tidak menjadi zombie (yang membuat os.kill(pid, 0) tetap "hidup").
        threading.Thread(target=proc.wait, daemon=True).start()

        cls.RUNNING_FILE.write_text(
            json.dumps(
                {
                    "started_at": datetime.now().isoformat(timespec="seconds"),
                    "pid": proc.pid,
                }
            ),
            encoding="utf-8",
        )
        return True

    # =========================================================
    # RUN (hanya dipicu tombol, staff-only)
    # =========================================================

    @classmethod
    def run(cls, config=None):
        from apps.survey_analysis.pipeline.runner import run_pipeline

        out = run_pipeline(config)
        # Tulis signature SELALU (termasuk saat STOP), supaya data yang sama
        # tidak di-run ulang terus-menerus.
        cls._write_cache(cls.signature())
        return out

    # =========================================================
    # LOAD (parse file output -> struktur tampilan)
    # =========================================================

    @staticmethod
    def _load_json(rel_path):
        path = cfg.OUTPUT_DIR / rel_path
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None

    @staticmethod
    def _load_csv(rel_path):
        path = cfg.OUTPUT_DIR / rel_path
        if not path.exists():
            return None
        try:
            return pd.read_csv(path)
        except (ValueError, OSError):
            return None

    @classmethod
    def context(cls):
        """Data siap-render untuk template ML Dashboard."""
        has_results = cls.has_results()
        stale = cls.is_stale()
        cache = cls._read_cache()
        generated_at = cache.get("generated_at") if cache else None

        ctx = {
            "has_results": has_results,
            "stale": stale,
            "running": cls.is_running(),
            "stop_message": None,
            "generated_at": generated_at,
            "sem_fit": None,
            "paths": [],
            "cfa_fit": None,
            "reliability": [],
            "lca_selected": None,
            "lca_reason": None,
            "lca_review_required": False,
            "lca_classes": [],
            "lca_profiles": {},
            "lca_model_comparison": [],
            "lca_entropy": None,
            "lca_class_colors": [],
            "lca_scatter": [],
            "lca_shap_per_class": [],
            "shap_top": [],
        }

        if not has_results:
            return ctx

        # ---- STOP message (pipeline berhenti di reliability/CFA/ML) ----
        state_raw = cls._load_json("reports/pipeline_state.json")
        if state_raw:
            for h in reversed(state_raw.get("state", [])):
                if h.get("status") == "STOPPED" and h.get("message"):
                    ctx["stop_message"] = h["message"]
                    break

        # ---- CFA fit (strip kualitas) ----
        cfa_raw = cls._load_json("cfa/fit_indices.json")
        if cfa_raw:
            ctx["cfa_fit"] = {
                "cfi": _r(cfa_raw.get("cfi")),
                "tli": _r(cfa_raw.get("tli")),
                "rmsea": _r(cfa_raw.get("rmsea")),
                "srmr": _r(cfa_raw.get("srmr")),
            }

        # ---- Reliability ----
        rel = cls._load_csv("reliability/reliability_results.csv")
        if rel is not None and not rel.empty:
            ctx["reliability"] = [
                {
                    "construct": row["construct"],
                    "name": row["name"],
                    "n_items": int(row["n_items"]),
                    "cronbach_alpha": _r(row["cronbach_alpha"]),
                    "omega": _r(row["omega"]),
                    "status": row["status"],
                }
                for _, row in rel.iterrows()
            ]

        # ---- SEM ----
        sem_raw = cls._load_json("cfa/sem_fit_indices.json")
        if sem_raw:
            dof = sem_raw.get("dof")
            ctx["sem_fit"] = {
                "cfi": _r(sem_raw.get("cfi")),
                "tli": _r(sem_raw.get("tli")),
                "rmsea": _r(sem_raw.get("rmsea")),
                "chi2": _r(sem_raw.get("chi2"), 1),
                "dof": int(dof) if dof is not None else None,
            }
        paths = cls._load_csv("cfa/path_coefficients.csv")
        if paths is not None and not paths.empty:
            ctx["paths"] = [
                {
                    "lhs": row["lhs"],
                    "rhs": row["rhs"],
                    "est": _r(row["est"], 2),
                    "se": _r(row["se"], 3),
                    "p_value": _r(row["p_value"], 4),
                    "standardized": _r(row["standardized"], 2),
                }
                for _, row in paths.iterrows()
            ]

        # ---- LCA ----
        selection = cls._load_json("lca/selection.json")
        if selection:
            ctx["lca_selected"] = selection.get("selected")
            ctx["lca_reason"] = selection.get("reason")
            ctx["lca_review_required"] = bool(
                selection.get("review_required")
            )
        lca_classes = cls._load_csv("lca/classification_diagnostics.csv")
        if lca_classes is not None and not lca_classes.empty:
            ctx["lca_classes"] = [
                {
                    "class": int(row["class"]),
                    "class_size": int(row["class_size"]),
                    "class_percentage": _r(row["class_percentage"], 1),
                    "avepp": _r(row["average_posterior_probability"]),
                    "color": color_for_index(int(row["class"])),
                }
                for _, row in lca_classes.iterrows()
            ]
        profiles = cls._load_json("lca/class_profiles.json")
        if profiles:
            ctx["lca_profiles"] = profiles

        # ---- LCA model comparison (BIC/AIC/entropy per jumlah kelas) ----
        comparison = cls._load_csv("lca/model_comparison.csv")
        if comparison is not None and not comparison.empty:
            ctx["lca_model_comparison"] = [
                {
                    "classes": int(row["classes"]),
                    "aic": _r(row["aic"], 1),
                    "bic": _r(row["bic"], 1),
                    "entropy": _r(row["entropy"]),
                    "min_class_pct": _r(row["min_class_pct"], 1),
                }
                for _, row in comparison.iterrows()
            ]
            # Entropy keseluruhan = entropy pada jumlah kelas yang terpilih.
            selected = ctx.get("lca_selected")
            if selected is not None:
                for item in ctx["lca_model_comparison"]:
                    if item["classes"] == selected:
                        ctx["lca_entropy"] = item["entropy"]
                        break

        # ---- Warna kelas LCA (fixed: kelas c -> palet[c]) ----
        ctx["lca_class_colors"] = [
            color_for_index(c) for c in range(ctx["lca_selected"] or 0)
        ]

        # ---- Scatter responden per kelas LCA (PCA 2D) ----
        scatter = cls._load_csv("lca/scatter_points.csv")
        if scatter is not None and not scatter.empty:
            ctx["lca_scatter"] = [
                {
                    "respondent_id": row["respondent_id"],
                    "class": int(row["class"]),
                    "x": _r(row["x"], 3),
                    "y": _r(row["y"], 3),
                }
                for _, row in scatter.iterrows()
            ]

        # ---- SHAP per kelas LCA ----
        per_class = cls._load_csv("shap/feature_importance_per_class.csv")
        if per_class is not None and not per_class.empty:
            ctx["lca_shap_per_class"] = [
                {
                    "class": int(row["class"]),
                    "feature": row["feature"],
                    "mean_abs_shap": _r(row["mean_abs_shap"], 4),
                }
                for _, row in per_class.iterrows()
            ]

        # ---- SHAP (top N item) ----
        shap = cls._load_csv("shap/feature_importance.csv")
        if shap is not None and not shap.empty:
            ctx["shap_top"] = [
                {
                    "feature": row["feature"],
                    "mean_abs_shap": _r(row["mean_abs_shap"], 4),
                    "rank": int(row["rank"]),
                    "direction": row["dominant_direction"],
                    "class": row["most_affected_class"],
                }
                for _, row in shap.head(12).iterrows()
            ]

        return ctx
