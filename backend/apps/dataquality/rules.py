"""
Konstanta aturan validasi kualitas data.

Naikkan RULES_VERSION setiap kali aturan di modul ini atau di
``validators.py`` / ``verification.py`` berubah, supaya satu eksekusi
selalu dapat ditelusuri ke aturan yang dipakainya.
"""

RULES_VERSION = "1.0.0"

CHECKPOINT_P1 = "P1"
CHECKPOINT_P2 = "P2"

# Empat dimensi -- tidak boleh ditambah.
COMPLETENESS = "completeness"
VALIDITY = "validity"
CONSISTENCY = "consistency"
UNIQUENESS = "uniqueness"

DIMENSIONS = (COMPLETENESS, VALIDITY, CONSISTENCY, UNIQUENESS)

# Nama kolom identitas (huruf kecil, sama seperti kunci column_map
# di ResponseBulkImportService).
COL_ID = "id resp"
COL_DESA = "desa"
COL_RT = "rt"
COL_PERSON = "person"

IDENTITY_COLUMNS = (COL_ID, COL_DESA, COL_RT, COL_PERSON)

DISPLAY_NAMES = {
    COL_ID: "ID Resp",
    COL_DESA: "Desa",
    COL_RT: "RT",
    COL_PERSON: "Person",
}

COL_COMBO = "Desa+RT+Person"

INDICATOR_MIN = 1
INDICATOR_MAX = 5


def display_name(column):
    return DISPLAY_NAMES.get(column, column.upper())
