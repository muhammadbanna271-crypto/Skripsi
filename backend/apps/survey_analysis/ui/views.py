"""UI dashboard pipeline analisis survei.

Menampilkan konfigurasi (engine selection), status pipeline, dan hasil
(sebagai ringkasan + link ke final report). Run pipeline via management command
atau tombol POST (sinkron — perlu beberapa menit).
"""

import json

from django.shortcuts import render

from apps.survey_analysis.config import settings as cfg
from apps.survey_analysis.cfa import SEM_REGISTRY
from apps.survey_analysis.ml import ML_REGISTRY
from apps.survey_analysis.lca import LCA_REGISTRY


def _engine_rows(registry):
    return [
        {
            "name": name,
            "available": cls.availability_error() is None,
            "error": cls.availability_error(),
        }
        for name, cls in registry.items()
    ]


def _read_state():
    path = cfg.OUTPUT_DIR / "reports" / "pipeline_state.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("state", data) if isinstance(data, dict) else data
    except (ValueError, OSError):
        return None


def _read_report():
    path = cfg.OUTPUT_DIR / "reports" / "final_report.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def dashboard(request):
    state = _read_state()
    report = _read_report()
    context = {
        "sem_engines": _engine_rows(SEM_REGISTRY),
        "lca_engines": _engine_rows(LCA_REGISTRY),
        "ml_engines": _engine_rows(ML_REGISTRY),
        "random_state": cfg.RANDOM_STATE,
        "state": state,
        "report": report,
        "output_dir": str(cfg.OUTPUT_DIR),
    }
    return render(request, "survey_analysis/dashboard.html", context)
