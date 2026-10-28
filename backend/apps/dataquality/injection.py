"""
Injeksi cacat untuk evaluasi deteksi. SATU jenis cacat per pemanggilan.

Keluaran: workbook cacat + ground truth (JSON) yang memuat seed,
sehingga lokasi cacat dapat direproduksi. Dataset sumber tidak diubah.

Jenis (defect):
  missing_value  -> completeness   (sel indikator dikosongkan)
  wrong_type     -> validity       (indikator menjadi teks, mis. 3 -> "3")
  out_of_range   -> validity       (indikator 0 / 6 / -1 / ...)
  duplicate      -> uniqueness     (variant: row | id | combo)
  missing_column -> schema gate    (variant: drop)  /
                    completeness   (variant: blank)
  unknown_village-> consistency    (kode Desa tidak ada di master)
"""

import json
import random

from openpyxl import load_workbook

from apps.response.services.bulk_import_service import (
    ResponseBulkImportService,
)

from .reader import as_integer, is_blank, read_bytes, sha256_of
from .rules import (
    COL_COMBO,
    COL_DESA,
    COL_ID,
    COL_PERSON,
    COL_RT,
    IDENTITY_COLUMNS,
)

DEFECT_TYPES = (
    "missing_value",
    "wrong_type",
    "out_of_range",
    "duplicate",
    "missing_column",
    "unknown_village",
)

EXPECTED_DIMENSION = {
    "missing_value": "completeness",
    "wrong_type": "validity",
    "out_of_range": "validity",
    "duplicate": "uniqueness",
    "missing_column": "schema_gate",
    "unknown_village": "consistency",
}

OUT_OF_RANGE_VALUES = (0, 6, -1, 7, 10)


def _record(respondent_id, row, column, defect, original, injected):
    return {
        "respondent_id": respondent_id,
        "row": row,
        "column": column,
        "defect_type": defect,
        "original_value": original,
        "injected_value": injected,
    }


def inject(source, out_path, truth_path, defect, *, seed, count=10,
           variant=None, known_village_codes=None):
    """
    source             : path / bytes / file-like workbook bersih
    out_path           : lokasi workbook cacat
    truth_path         : lokasi ground truth (JSON)
    count              : jumlah rekaman/sel/kolom yang dirusak
    known_village_codes: kode desa master; kode "asing" dipilih di luar itu
    Return: dict ground truth.
    """

    if defect not in DEFECT_TYPES:
        raise ValueError(f"defect harus salah satu dari {DEFECT_TYPES}")

    data, _ = read_bytes(source)

    from io import BytesIO

    wb = load_workbook(BytesIO(data), data_only=True)
    ws = wb.active

    header_row, column_map = ResponseBulkImportService._find_header_columns(ws)

    indicator_cols = sorted(
        name for name in column_map if name not in IDENTITY_COLUMNS
    )

    data_rows = [
        r for r in range(header_row + 1, ws.max_row + 1)
        if not is_blank(ws.cell(row=r, column=column_map[COL_ID]).value)
    ]

    rng = random.Random(seed)
    records = []

    def cell(row, name):
        return ws.cell(row=row, column=column_map[name])

    def rid(row):
        return as_integer(cell(row, COL_ID).value)

    if defect in ("missing_value", "wrong_type", "out_of_range"):

        targets = set()
        total = len(data_rows) * len(indicator_cols)
        count = min(count, total)

        while len(targets) < count:
            targets.add((rng.choice(data_rows), rng.choice(indicator_cols)))

        for row, name in sorted(targets):
            target = cell(row, name)
            original = target.value
            if defect == "missing_value":
                injected = None
            elif defect == "wrong_type":
                injected = str(original)
            else:
                injected = rng.choice(OUT_OF_RANGE_VALUES)
            target.value = injected
            records.append(
                _record(rid(row), row, name.upper(), defect, original, injected)
            )

    elif defect == "duplicate":

        variant = variant or "row"
        chosen = sorted(rng.sample(data_rows, min(count, len(data_rows))))

        if variant == "row":
            next_row = ws.max_row + 1
            for row in chosen:
                for name, col in column_map.items():
                    ws.cell(row=next_row, column=col).value = (
                        ws.cell(row=row, column=col).value
                    )
                records.append(
                    _record(rid(row), next_row, "ID Resp", defect,
                            rid(row), rid(row))
                )
                next_row += 1

        elif variant in ("id", "combo"):
            # Baris yang diubah selalu SESUDAH baris yang ditiru,
            # sehingga baris yang ditolak (kemunculan kedua) tertentu.
            chosen_set = set(chosen)
            for row in chosen:
                candidates = [
                    r for r in data_rows if r < row and r not in chosen_set
                ]
                if not candidates:
                    continue
                twin = rng.choice(candidates)
                if variant == "id":
                    original = rid(row)
                    cell(row, COL_ID).value = rid(twin)
                    records.append(
                        _record(original, row, "ID Resp", defect,
                                original, rid(twin))
                    )
                else:
                    keys = (COL_DESA, COL_RT, COL_PERSON)
                    original = "|".join(str(cell(row, k).value) for k in keys)
                    injected = "|".join(str(cell(twin, k).value) for k in keys)
                    for k in keys:
                        cell(row, k).value = cell(twin, k).value
                    records.append(
                        _record(rid(row), row, COL_COMBO, defect,
                                original, injected)
                    )
        else:
            raise ValueError("variant duplicate: row | id | combo")

    elif defect == "missing_column":

        variant = variant or "drop"
        names = rng.sample(indicator_cols, min(count, len(indicator_cols)))

        if variant == "blank":
            for name in sorted(names):
                for row in data_rows:
                    original = cell(row, name).value
                    cell(row, name).value = None
                    records.append(
                        _record(rid(row), row, name.upper(), defect,
                                original, None)
                    )
        elif variant == "drop":
            # Hapus dari kolom paling kanan agar indeks kolom lain tidak
            # bergeser selama penghapusan.
            for name in sorted(names, key=lambda n: -column_map[n]):
                col = column_map[name]
                header_text = ws.cell(row=header_row, column=col).value
                ws.delete_cols(col)
                records.append(
                    _record(None, header_row, name.upper(), defect,
                            header_text, None)
                )
            records.sort(key=lambda r: r["column"])
        else:
            raise ValueError("variant missing_column: drop | blank")

    elif defect == "unknown_village":

        known = {
            int(code) for code in (known_village_codes or [])
            if str(code).isdigit()
        }
        existing = {
            as_integer(cell(r, COL_DESA).value) for r in data_rows
        } - {None}
        top = max(known | existing | {0})

        for row in sorted(rng.sample(data_rows, min(count, len(data_rows)))):
            original = cell(row, COL_DESA).value
            injected = top + rng.randint(1, 900)
            cell(row, COL_DESA).value = injected
            records.append(
                _record(rid(row), row, "Desa", defect, original, injected)
            )

    wb.save(out_path)

    truth = {
        "seed": seed,
        "defect_type": defect,
        "variant": variant,
        "expected_dimension": EXPECTED_DIMENSION[defect],
        "count": len(records),
        "source_sha256": sha256_of(data),
        "records": records,
    }

    with open(truth_path, "w", encoding="utf-8") as handle:
        json.dump(truth, handle, indent=2, ensure_ascii=False, default=str)

    return truth


def write_clean(source, out_path, truth_path, *, seed=0):
    """
    Dataset bersih sebagai kontrol: salinan sumber + ground truth tanpa
    cacat (defect_type "clean"), untuk mengukur false positive.
    """

    data, _ = read_bytes(source)

    with open(out_path, "wb") as handle:
        handle.write(data)

    truth = {
        "seed": seed,
        "defect_type": "clean",
        "variant": None,
        "expected_dimension": None,
        "count": 0,
        "source_sha256": sha256_of(data),
        "records": [],
    }

    with open(truth_path, "w", encoding="utf-8") as handle:
        json.dump(truth, handle, indent=2)

    return truth
