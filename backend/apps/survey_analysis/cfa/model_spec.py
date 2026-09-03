"""Membangun spesifikasi model (measurement + structural) dari config.

Menghasilkan string deskripsi model dengan sintaks yang dipahami engine
(semopy dan lavaan memakai sintaks `=~` / `~` yang sama). Config konstruk +
jalur di model_config sehingga struktur dapat diubah tanpa mengubah kode.
"""

from collections import defaultdict

from apps.survey_analysis.config import model_config


def build_model_description(measurement_only=False):
    """Bangun deskripsi model SEM.

    measurement_only=True  -> hanya measurement model (CFA), semua laten
                              eksogen (saling berkorelasi default).
    measurement_only=False -> measurement + structural (24 jalur).
    """
    lines = []

    # ---- Measurement model: konstruk =~ item-item ----
    for code in model_config.construct_order():
        items = model_config.CONSTRUCTS[code]["items"]
        lines.append(f"{code} =~ {' + '.join(items)}")

    # ---- Structural model: jalur regresi antar laten ----
    if not measurement_only:
        by_target = defaultdict(list)
        for src, dst in model_config.PATHS:
            by_target[dst].append(src)
        for dst in model_config.construct_order():
            if dst in by_target:
                lines.append(f"{dst} ~ {' + '.join(by_target[dst])}")

    return "\n".join(lines)


def measurement_model_summary():
    """Ringkas measurement model untuk report/UI."""
    return {
        code: {
            "name": model_config.name_of(code),
            "role": model_config.role_of(code),
            "n_items": len(model_config.CONSTRUCTS[code]["items"]),
            "items": model_config.CONSTRUCTS[code]["items"],
        }
        for code in model_config.construct_order()
    }


def structural_model_summary():
    """Ringkas structural model: grup jalur per target."""
    by_target = defaultdict(list)
    for src, dst in model_config.PATHS:
        by_target[dst].append(src)
    return {
        "n_paths": len(model_config.PATHS),
        "paths": [{"target": dst, "sources": by_target[dst]} for dst in model_config.construct_order() if dst in by_target],
    }
