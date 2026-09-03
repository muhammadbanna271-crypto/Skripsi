"""Menulis hasil ke outputs/ (CSV + JSON) sesuai struktur yang ditentukan."""

import json

import pandas as pd

from apps.survey_analysis.config import settings as cfg


def _ensure_dirs():
    cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for sub in cfg.OUTPUT_SUBDIRS:
        (cfg.OUTPUT_DIR / sub).mkdir(parents=True, exist_ok=True)


def write_csv(df, subdir, filename):
    """Tulis DataFrame ke outputs/<subdir>/<filename>.csv."""
    _ensure_dirs()
    path = cfg.OUTPUT_DIR / subdir / filename
    if df is not None and not df.empty:
        df.to_csv(path, index=False)
    else:
        pd.DataFrame().to_csv(path, index=False)
    return path


def write_json(obj, subdir, filename):
    """Tulis objek serializable ke outputs/<subdir>/<filename>.json."""
    _ensure_dirs()
    path = cfg.OUTPUT_DIR / subdir / filename

    def _clean(o):
        if isinstance(o, (pd.DataFrame, pd.Series)):
            return o.to_dict(orient="records")
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_clean(x) for x in o]
        if isinstance(o, (int, float, str, bool)) or o is None:
            return o
        return str(o)

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(_clean(obj), fh, ensure_ascii=False, indent=2, default=str)
    return path
