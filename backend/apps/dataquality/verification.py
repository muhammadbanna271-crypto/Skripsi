"""
P2 -- verifikasi data yang benar-benar tersimpan terhadap sumber.

Hanya membaca database. Setiap rekaman yang lolos P1 dicocokkan dengan
Respondent/Response hasil import existing:

- tidak ditemukan -> "hilang" (dihitung di n_lost, bukan penolakan);
- ditemukan tetapi isinya tidak sama dengan sumber / tidak valid ->
  ditolak di P2 (dan dihapus oleh pipeline agar tidak ikut skoring).
"""

import re
from dataclasses import dataclass, field

from apps.respondent.models import Respondent
from apps.response.models import Response

from .reader import as_integer
from .rules import (
    CHECKPOINT_P2,
    COL_DESA,
    COL_ID,
    COL_PERSON,
    COL_RT,
    COMPLETENESS,
    CONSISTENCY,
    INDICATOR_MAX,
    INDICATOR_MIN,
    UNIQUENESS,
    VALIDITY,
    display_name,
)
from .validators import Violation, new_counts, person_key

ADDRESS_PATTERN = re.compile(r", RT (.*?) - Jabatan: (.*)$", re.S)

RULE_LOST = "record_not_stored"

# Nilai db_value bila sel/record memang tidak ada di database.
ABSENT = "<tidak ada>"

ACTION_NONE = ""
ACTION_NOT_STORED = "not_stored"
ACTION_REMOVED = "removed_from_scoring_tables"


def nik_for(id_resp):
    # Harus sama dengan ResponseBulkImportService._resolve_respondent.
    return f"IMPORT-{int(id_resp)}"


@dataclass
class VerificationResult:
    violations: list = field(default_factory=list)
    counts: dict = field(default_factory=new_counts)
    lost_rows: set = field(default_factory=set)
    rejected_rows: set = field(default_factory=set)
    verified_rows: list = field(default_factory=list)
    # Respondent.id yang harus dibuang karena ditolak di P2.
    rejected_respondent_ids: list = field(default_factory=list)


def stored_numeric(response):
    """Nilai tersimpan sebagai angka menurut tipe jawaban kuesioner."""

    answer_type = response.questionnaire.answer_type

    if answer_type in ("likert", "integer"):
        return response.answer_integer
    if answer_type == "decimal":
        return (
            float(response.answer_decimal)
            if response.answer_decimal is not None
            else None
        )
    if answer_type == "boolean":
        if response.answer_boolean is None:
            return None
        return float(response.score)
    return None


def stored_matches(response, source_value):
    answer_type = response.questionnaire.answer_type
    source = as_integer(source_value)

    if answer_type == "boolean":
        return response.answer_boolean == bool(source)

    stored = stored_numeric(response)
    return stored is not None and float(stored) == float(source)


def parse_address(address):
    match = ADDRESS_PATTERN.search(address or "")
    if not match:
        return None, None
    return match.group(1), match.group(2)


def run_p2(accepted_rows, indicator_codes):
    """accepted_rows: list[SourceRow] yang lolos P1."""

    result = VerificationResult()
    counts = result.counts

    niks = {row.row_number: nik_for(row.values[COL_ID]) for row in accepted_rows}

    respondents = {
        respondent.nik: respondent
        for respondent in (
            Respondent.objects
            .filter(nik__in=list(niks.values()))
            .select_related("survey_village__village")
        )
    }

    responses = {}

    for response in (
        Response.objects
        .filter(respondent__in=[r.id for r in respondents.values()])
        .select_related("questionnaire__indicator")
    ):
        key = (response.respondent_id, response.questionnaire.indicator.code.lower())
        responses[key] = response

    stored_combos = set()

    for row in accepted_rows:

        rid = str(as_integer(row.values[COL_ID]))
        respondent = respondents.get(niks[row.row_number])
        bad = []

        def flag(column, dimension, rule, reason, value, db_value,
                 row=row, rid=rid):
            bad.append(
                Violation(
                    CHECKPOINT_P2,
                    row.row_number,
                    rid,
                    display_name(column),
                    value,
                    dimension,
                    rule,
                    reason,
                    db_value=db_value,
                )
            )

        n_cells = 4 + len(indicator_codes)

        counts[COMPLETENESS].checked += n_cells
        counts[CONSISTENCY].checked += 1
        counts[UNIQUENESS].checked += 1

        if respondent is None:
            # Hilang / tertimpa: seluruh sel tidak terpenuhi.
            flag(
                COL_ID,
                UNIQUENESS,
                RULE_LOST,
                "Data pada baris ini lolos pemeriksaan awal, tetapi tidak "
                "ditemukan di database setelah proses penyimpanan. Data "
                "ini tidak tersimpan.",
                row.values.get(COL_ID),
                ABSENT,
            )
            result.violations.extend(bad)
            result.lost_rows.add(row.row_number)
            continue

        # ---- identitas tersimpan --------------------------------
        village = respondent.survey_village.village
        stored_rt, stored_person = parse_address(respondent.address)

        src_desa = as_integer(row.values[COL_DESA])
        src_rt = as_integer(row.values[COL_RT])
        src_person = row.values[COL_PERSON]

        identity_ok = True

        counts[COMPLETENESS].satisfied += 1  # ID: respondent ada

        for column, present in (
            (COL_DESA, village is not None and village.code != ""),
            (COL_RT, stored_rt not in (None, "")),
            (COL_PERSON, stored_person not in (None, "")),
        ):
            if present:
                counts[COMPLETENESS].satisfied += 1
            else:
                flag(
                    column,
                    COMPLETENESS,
                    "stored_cell_missing",
                    f"Isian kolom {display_name(column)} ada di file, "
                    "tetapi tidak ditemukan pada data yang tersimpan.",
                    row.values.get(column),
                    ABSENT,
                )

        if village.code != str(src_desa):
            identity_ok = False
            flag(
                COL_DESA,
                CONSISTENCY,
                "stored_value_mismatch",
                f"Kode Desa di database ({village.code}) berbeda dengan "
                f"yang ada di file ({src_desa}).",
                row.values[COL_DESA],
                village.code,
            )

        try:
            stored_rt_int = int(float(stored_rt))
        except (TypeError, ValueError):
            stored_rt_int = None

        rt_matches = stored_rt_int is not None and stored_rt_int == src_rt

        if not rt_matches:
            identity_ok = False
            flag(
                COL_RT,
                CONSISTENCY,
                "stored_value_mismatch",
                f"RT di database ({stored_rt}) berbeda dengan yang ada "
                f"di file ({src_rt}).",
                row.values[COL_RT],
                stored_rt,
            )

        if stored_person is None or stored_person != str(src_person):
            identity_ok = False
            flag(
                COL_PERSON,
                CONSISTENCY,
                "stored_value_mismatch",
                f"Person di database ({stored_person}) berbeda dengan "
                f"yang ada di file ({src_person}).",
                src_person,
                stored_person,
            )

        # Validitas identitas tersimpan (hanya sel yang terisi): Desa selalu
        # kode master (FK); RT harus bilangan bulat; Person tidak kosong.
        counts[VALIDITY].checked += 1
        counts[VALIDITY].satisfied += 1

        if stored_rt not in (None, ""):
            counts[VALIDITY].checked += 1
            if stored_rt_int is not None:
                counts[VALIDITY].satisfied += 1
            else:
                flag(
                    COL_RT,
                    VALIDITY,
                    "stored_rt_integer",
                    f"RT yang tersimpan di database ({stored_rt}) bukan "
                    "angka bulat.",
                    row.values[COL_RT],
                    stored_rt,
                )

        if stored_person not in (None, ""):
            counts[VALIDITY].checked += 1
            counts[VALIDITY].satisfied += 1

        # ---- jawaban tersimpan ----------------------------------
        values_ok = True

        for code in indicator_codes:

            response = responses.get((respondent.id, code))
            source_value = row.values.get(code)

            if response is None or stored_numeric_missing(response):
                flag(
                    code,
                    COMPLETENESS,
                    "stored_cell_missing",
                    f"Jawaban kolom {display_name(code)} ada di file, "
                    "tetapi tidak ditemukan pada data yang tersimpan.",
                    source_value,
                    ABSENT,
                )
                values_ok = False
                continue

            counts[COMPLETENESS].satisfied += 1
            counts[VALIDITY].checked += 1

            stored = stored_numeric(response)
            stored_int = as_integer(stored) if stored is not None else None

            if response.questionnaire.answer_type == "text" or (
                stored_int is None
                or not INDICATOR_MIN <= stored_int <= INDICATOR_MAX
            ):
                flag(
                    code,
                    VALIDITY,
                    "stored_indicator_invalid",
                    f"Nilai yang tersimpan di database ({stored}) bukan "
                    f"angka bulat {INDICATOR_MIN} sampai {INDICATOR_MAX}.",
                    source_value,
                    stored,
                )
                values_ok = False
            else:
                counts[VALIDITY].satisfied += 1

            if not stored_matches(response, source_value):
                values_ok = False
                flag(
                    code,
                    CONSISTENCY,
                    "stored_value_mismatch",
                    f"Nilai di database ({stored}) berbeda dengan yang "
                    f"ada di file ({source_value}).",
                    source_value,
                    stored,
                )

        # ---- consistency & uniqueness rekaman -------------------
        if identity_ok and values_ok:
            counts[CONSISTENCY].satisfied += 1

        combo = (village.code, stored_rt, person_key(stored_person or ""))

        if combo in stored_combos:
            flag(
                COL_ID,
                UNIQUENESS,
                "stored_combo_duplicate",
                "Kombinasi Desa, RT, dan Person yang sama tersimpan "
                "lebih dari satu kali di database.",
                row.values.get(COL_ID),
                f"Desa={village.code}, RT={stored_rt}, Person={stored_person}",
            )
        else:
            counts[UNIQUENESS].satisfied += 1
        stored_combos.add(combo)

        result.violations.extend(bad)

        if bad:
            result.rejected_rows.add(row.row_number)
            result.rejected_respondent_ids.append(respondent.id)
        else:
            result.verified_rows.append(row)

    return result


def stored_numeric_missing(response):
    answer_type = response.questionnaire.answer_type
    if answer_type == "text":
        return not response.answer_text
    return stored_numeric(response) is None
