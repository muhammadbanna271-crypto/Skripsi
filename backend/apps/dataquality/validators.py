"""
P1 -- validasi data sumber sebelum disimpan.

Empat dimensi, satuan sesuai spesifikasi:
- completeness : sel     (kosong/null/NaN pada kolom wajib)
- validity     : sel     (tipe/domain; hanya sel yang terisi)
- consistency  : rekaman (kode Desa terdaftar di master)
- uniqueness   : rekaman (ID Resp; kombinasi Desa+RT+Person)

Satuan penolakan = baris responden. Tidak ada imputasi/perbaikan nilai.
Duplikat: kemunculan pertama dipertahankan, berikutnya ditolak.
Consistency hanya diperiksa pada rekaman yang Desa-nya berupa bilangan
bulat, uniqueness hanya pada rekaman yang ID Resp-nya valid; sel yang
kosong/salah tipe sudah dicatat oleh completeness/validity sehingga
satu cacat tidak dihitung ganda pada dimensi lain.
"""

from dataclasses import dataclass, field
from typing import Any

from .reader import as_integer, is_blank
from .wording import shown
from .rules import (
    CHECKPOINT_P1,
    COL_COMBO,
    COL_DESA,
    COL_ID,
    COL_PERSON,
    COL_RT,
    COMPLETENESS,
    CONSISTENCY,
    DIMENSIONS,
    IDENTITY_COLUMNS,
    INDICATOR_MAX,
    INDICATOR_MIN,
    UNIQUENESS,
    VALIDITY,
    display_name,
)


@dataclass(frozen=True)
class Violation:
    checkpoint: str
    row_number: int
    respondent_id: str
    column: str
    value: Any
    dimension: str
    rule: str
    reason: str
    # P2: nilai yang ada di database (None = tidak berlaku, mis. P1).
    db_value: Any = None
    # P1 uniqueness: baris kemunculan pertama yang dipertahankan.
    related_row: Any = None
    # P2: tindakan terhadap rekaman (lihat verification.ACTION_*).
    record_action: str = ""


@dataclass
class DimensionCount:
    checked: int = 0
    satisfied: int = 0

    @property
    def score(self):
        return self.satisfied / self.checked if self.checked else None


def new_counts():
    return {dimension: DimensionCount() for dimension in DIMENSIONS}


@dataclass
class CheckResult:
    violations: list = field(default_factory=list)
    counts: dict = field(default_factory=new_counts)
    rejected_rows: set = field(default_factory=set)
    accepted_rows: list = field(default_factory=list)  # list[SourceRow]


def respondent_label(row):
    raw = row.values.get(COL_ID)
    if is_blank(raw):
        return f"baris-{row.row_number}"
    integer = as_integer(raw)
    return str(integer) if integer is not None else str(raw)


def person_key(value):
    return str(value).strip().lower()


def check_identity_validity(column, value, allowed_persons):
    """(rule, alasan) bila tidak valid, selain itu None. value tidak kosong."""

    if column == COL_ID:
        integer = as_integer(value)
        if integer is None or integer < 1:
            return (
                "id_resp_integer",
                "ID Resp harus berupa angka bulat mulai dari 1, tetapi yang "
                f"tertulis: {shown(value)}.",
            )
    elif column == COL_DESA:
        if as_integer(value) is None:
            return (
                "desa_integer",
                "Kode Desa harus berupa angka bulat (mis. 1, 2, 3), tetapi "
                f"yang tertulis: {shown(value)}.",
            )
    elif column == COL_RT:
        if as_integer(value) is None:
            return (
                "rt_integer",
                "RT harus berupa angka bulat, tetapi yang tertulis: "
                f"{shown(value)}.",
            )
    elif column == COL_PERSON:
        if isinstance(value, bool):
            return (
                "person_domain",
                "Isian Person tidak valid; tuliskan nama jabatan responden.",
            )
        if (
            allowed_persons is not None
            and person_key(value) not in allowed_persons
        ):
            return (
                "person_domain",
                f"Jabatan \"{shown(value)}\" pada kolom Person tidak "
                "dikenal sistem. Periksa kembali penulisannya.",
            )
    return None


def check_indicator_validity(column, value):
    """(rule, alasan) bila tidak valid, selain itu None. value tidak kosong."""

    name = display_name(column)
    integer = as_integer(value)
    if integer is None:
        return (
            "indicator_integer",
            f"Isian kolom {name} harus berupa angka bulat "
            f"{INDICATOR_MIN} sampai {INDICATOR_MAX}, tetapi yang tertulis "
            f"bukan angka bulat: {shown(value)}.",
        )
    if not INDICATOR_MIN <= integer <= INDICATOR_MAX:
        return (
            "indicator_range",
            f"Isian kolom {name} harus antara {INDICATOR_MIN} sampai "
            f"{INDICATOR_MAX}, tetapi yang tertulis: {shown(value)}.",
        )
    return None


def run_p1(rows, indicator_codes, village_codes, allowed_persons=None):
    """
    rows            : list[SourceRow]
    indicator_codes : kode indikator wajib (huruf kecil)
    village_codes   : set kode Village master (string)
    allowed_persons : set nilai Person (huruf kecil) atau None = tanpa batas
    """

    result = CheckResult()
    counts = result.counts

    required = list(IDENTITY_COLUMNS) + list(indicator_codes)

    seen_ids = {}     # ID Resp -> nomor baris kemunculan pertama
    seen_combos = {}  # (desa, rt, person) -> nomor baris pertama

    for row in rows:

        rid = respondent_label(row)
        flags = []

        def flag(column, dimension, rule, reason, related=None,
                 row=row, rid=rid):
            flags.append(
                Violation(
                    CHECKPOINT_P1,
                    row.row_number,
                    rid,
                    COL_COMBO if column == COL_COMBO else display_name(column),
                    row.values.get(column),
                    dimension,
                    rule,
                    reason,
                    related_row=related,
                )
            )

        # ---- completeness + validity (satuan sel) ----------------
        for column in required:

            value = row.values.get(column)

            counts[COMPLETENESS].checked += 1

            if is_blank(value):
                flag(
                    column,
                    COMPLETENESS,
                    "required_cell_missing",
                    f"Kolom {display_name(column)} masih kosong. Kolom ini "
                    "wajib diisi.",
                )
                continue

            counts[COMPLETENESS].satisfied += 1
            counts[VALIDITY].checked += 1

            if column in IDENTITY_COLUMNS:
                problem = check_identity_validity(
                    column, value, allowed_persons
                )
            else:
                problem = check_indicator_validity(column, value)

            if problem:
                flag(column, VALIDITY, problem[0], problem[1])
            else:
                counts[VALIDITY].satisfied += 1

        # ---- consistency (satuan rekaman) ------------------------
        desa = as_integer(row.values.get(COL_DESA))

        if desa is not None:
            counts[CONSISTENCY].checked += 1
            if str(desa) in village_codes:
                counts[CONSISTENCY].satisfied += 1
            else:
                flag(
                    COL_DESA,
                    CONSISTENCY,
                    "village_not_registered",
                    f"Kode Desa {desa} tidak terdaftar di data master "
                    "desa. Periksa kembali kode desanya.",
                )

        # ---- uniqueness (satuan rekaman) -------------------------
        id_int = as_integer(row.values.get(COL_ID))

        if id_int is not None and id_int >= 1:

            counts[UNIQUENESS].checked += 1
            unique = True

            if id_int in seen_ids:
                unique = False
                flag(
                    COL_ID,
                    UNIQUENESS,
                    "id_resp_duplicate",
                    f"ID Resp {id_int} sudah dipakai di baris "
                    f"{seen_ids[id_int]}. Baris {seen_ids[id_int]} dipakai "
                    "sebagai data utama, sedangkan baris ini dianggap ganda "
                    "dan tidak diproses.",
                    related=seen_ids[id_int],
                )
            seen_ids.setdefault(id_int, row.row_number)

            rt = as_integer(row.values.get(COL_RT))
            person = row.values.get(COL_PERSON)

            if desa is not None and rt is not None and not is_blank(person):

                combo = (desa, rt, person_key(person))

                if combo in seen_combos:
                    unique = False
                    flag(
                        COL_COMBO,
                        UNIQUENESS,
                        "desa_rt_person_duplicate",
                        "Kombinasi Desa, RT, dan Person yang sama sudah "
                        f"ada di baris {seen_combos[combo]}. Baris "
                        f"{seen_combos[combo]} dipakai sebagai data utama, "
                        "sedangkan baris ini dianggap ganda dan tidak "
                        "diproses.",
                        related=seen_combos[combo],
                    )
                seen_combos.setdefault(combo, row.row_number)

            if unique:
                counts[UNIQUENESS].satisfied += 1

        result.violations.extend(flags)

        if flags:
            result.rejected_rows.add(row.row_number)
        else:
            result.accepted_rows.append(row)

    return result
