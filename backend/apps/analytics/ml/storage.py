import os

import joblib
from django.conf import settings


MODEL_DIR = os.path.join(
    settings.BASE_DIR,
    "apps",
    "analytics",
    "ml_models",
)


def ensure_model_dir():

    os.makedirs(
        MODEL_DIR,
        exist_ok=True,
    )


def model_path(filename):

    ensure_model_dir()

    return os.path.join(
        MODEL_DIR,
        filename,
    )


def save_object(obj, filename):
    """
    Simpan object (model, scaler, dsb) ke disk pakai joblib.
    """

    path = model_path(filename)

    joblib.dump(obj, path)

    return path


def load_object(filename):
    """
    Load object dari disk. Return None kalau file belum ada
    (misal model belum pernah di-training).
    """

    path = model_path(filename)

    if not os.path.exists(path):
        return None

    return joblib.load(path)


def object_exists(filename):

    return os.path.exists(
        model_path(filename)
    )
