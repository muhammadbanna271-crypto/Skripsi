"""
Evaluasi deteksi (TP/FP/FN, precision, recall) dan perbandingan
fingerprint antar eksekusi. Hanya membaca log; tidak mengubah apa pun.

Satuan lokasi cacat dipilih menurut jenis cacat supaya satu cacat tidak
dihitung ganda ketika memicu beberapa rule:

  cell    : (source_row, kolom)  missing_value, wrong_type, out_of_range,
                                 unknown_village, missing_column/blank
  row     : source_row           duplicate (satu baris duplikat bisa
                                 melanggar ID Resp DAN Desa+RT+Person,
                                 tetap satu cacat)
  column  : nama kolom           missing_column/drop (ditangkap schema gate)
  clean   : dataset bersih -- tidak ada cacat, hanya false positive

Deteksi = rejection di titik P1 (pemeriksaan sumber). Discrepancy P2
dilaporkan terpisah karena bukan pendeteksian cacat sumber.
"""

from .models import ExecutionLog

UNIT_CELL = "cell"
UNIT_ROW = "row"
UNIT_COLUMN = "column"
UNIT_CLEAN = "clean"


def scenario_name(truth):
    variant = truth.get("variant")
    name = truth["defect_type"]
    return f"{name}:{variant}" if variant else name


def unit_of(truth):
    defect = truth["defect_type"]
    if defect == "clean":
        return UNIT_CLEAN
    if defect == "duplicate":
        return UNIT_ROW
    if defect == "missing_column" and truth.get("variant", "drop") == "drop":
        return UNIT_COLUMN
    return UNIT_CELL


def truth_locations(truth):
    unit = unit_of(truth)
    records = truth.get("records", [])
    if unit == UNIT_CELL:
        return {(r["row"], str(r["column"]).upper()) for r in records}
    if unit == UNIT_ROW:
        return {r["row"] for r in records}
    if unit == UNIT_COLUMN:
        return {str(r["column"]).upper() for r in records}
    return set()


def detected_locations(execution, unit):
    if unit == UNIT_COLUMN:
        return {
            str(c).upper()
            for c in execution.output_summary.get("missing_columns", [])
        }

    p1 = execution.rejections.filter(checkpoint="P1")

    if unit == UNIT_CELL:
        return {(r.source_row, r.column_name.upper()) for r in p1}
    return {r.source_row for r in p1}  # row & clean


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def evaluate(execution, truth):
    """TP/FP/FN + precision/recall. Dataset bersih: hanya FP (recall None)."""

    unit = unit_of(truth)
    expected = truth_locations(truth)
    found = detected_locations(execution, unit)

    tp = expected & found
    fp = found - expected
    fn = expected - found

    clean = unit == UNIT_CLEAN

    return {
        "scenario": scenario_name(truth),
        "unit": unit,
        "seed": truth.get("seed"),
        "tp": len(tp),
        "fp": len(fp),
        "fn": len(fn),
        "precision": _ratio(len(tp), len(tp) + len(fp)),
        "recall": None if clean else _ratio(len(tp), len(tp) + len(fn)),
        "tp_locations": sorted(tp, key=str),
        "fp_locations": sorted(fp, key=str),
        "fn_locations": sorted(fn, key=str),
    }


FINGERPRINT_KEYS = (
    ("respondents_sha256", "n_respondents", "Responden"),
    ("answers_sha256", "n_answers", "Jawaban"),
    ("scores_sha256", "n_scores", "Skor"),
)


def compare_executions(a, b):
    """
    Bandingkan dua eksekusi: apakah masukannya sama dan apakah keadaan
    akhir (fingerprint) sama. Dipakai untuk determinisme (input + konfigurasi
    sama pada database yang direset) dan idempotensi (dataset sama diunggah
    dua kali pada database yang sama).
    """

    state_a = a.output_summary.get("database_state", {})
    state_b = b.output_summary.get("database_state", {})

    context = {
        "same_source_sha256": a.source_sha256 == b.source_sha256,
        "same_rules_version": a.rules_version == b.rules_version,
        "same_config": a.output_summary.get("config")
        == b.output_summary.get("config"),
        "same_counts": (
            (a.n_input, a.n_accepted, a.n_rejected, a.n_lost, a.n_output)
            == (b.n_input, b.n_accepted, b.n_rejected, b.n_lost, b.n_output)
        ),
    }

    components = []
    for hash_key, count_key, label in FINGERPRINT_KEYS:
        components.append(
            {
                "label": label,
                "hash_a": state_a.get(hash_key),
                "hash_b": state_b.get(hash_key),
                "count_a": state_a.get(count_key),
                "count_b": state_b.get(count_key),
                "same": (
                    state_a.get(hash_key) is not None
                    and state_a.get(hash_key) == state_b.get(hash_key)
                    and state_a.get(count_key) == state_b.get(count_key)
                ),
            }
        )

    comparable = all(
        e.status == ExecutionLog.STATUS_SUCCESS for e in (a, b)
    )

    return {
        "comparable": comparable,
        "context": context,
        "components": components,
        "all_same": comparable and all(c["same"] for c in components),
    }
