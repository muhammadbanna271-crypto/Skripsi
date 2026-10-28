"""
Teks untuk pengguna awam (bahasa sehari-hari yang tetap formal).

Kode aturan teknis (mis. ``indicator_range``) tetap disimpan di log untuk
peneliti; modul ini hanya menerjemahkannya menjadi kalimat yang mudah
dipahami dan menyusun pesan hasil impor.
"""

MAX_EXAMPLES = 5
MAX_NAMES = 10


def shown(value, limit=40):
    """Tampilkan nilai sel apa adanya (dipotong bila terlalu panjang)."""
    text = "kosong" if value is None else str(value)
    return text if len(text) <= limit else text[:limit] + "..."


def name_list(names, limit=MAX_NAMES):
    names = list(names)
    if len(names) <= limit:
        return ", ".join(names)
    return f"{', '.join(names[:limit])}, dan {len(names) - limit} lainnya"


# Nama masalah dalam bahasa sehari-hari, dipakai pada ringkasan.
RULE_LABELS = {
    "required_cell_missing": "ada isian yang masih kosong",
    "indicator_integer": "ada isian yang bukan angka bulat (teks atau desimal)",
    "indicator_range": "ada angka di luar rentang 1 sampai 5",
    "id_resp_integer": "ID Resp bukan angka bulat",
    "desa_integer": "kode Desa bukan angka bulat",
    "rt_integer": "RT bukan angka bulat",
    "person_domain": "isian Person tidak dikenal",
    "village_not_registered": "kode Desa tidak terdaftar di data master",
    "id_resp_duplicate": "ID Resp ganda",
    "desa_rt_person_duplicate": "kombinasi Desa, RT, dan Person ganda",
    "record_not_stored": "data gagal tersimpan di database",
    "stored_value_mismatch": "data di database berbeda dengan isi file",
    "stored_cell_missing": "sebagian isian tidak tersimpan di database",
    "stored_indicator_invalid": "nilai yang tersimpan di database tidak valid",
    "stored_rt_integer": "RT yang tersimpan bukan angka bulat",
    "stored_combo_duplicate": "kombinasi Desa, RT, dan Person ganda di database",
}


def rule_label(rule):
    return RULE_LABELS.get(rule, rule)


# Pesan kegagalan (dipakai pada ExecutionLog.output_summary["user_message"]).
MSG_NO_QUESTIONNAIRE = (
    "Belum ada kuesioner aktif di data master, sehingga sistem tidak tahu "
    "kolom indikator apa saja yang harus ada di file. Tambahkan Questionnaire "
    "(satu untuk setiap indikator, dengan status Active) melalui menu "
    "Questionnaire, lalu impor kembali file ini."
)

MSG_UNREADABLE_FILE = (
    "File tidak dapat dibuka. Pastikan file berformat Excel (.xlsx), tidak "
    "rusak, dan tidak sedang dilindungi kata sandi."
)

MSG_UNEXPECTED = (
    "Terjadi kesalahan di sistem saat memproses file. Data yang sudah masuk "
    "mungkin belum lengkap. Mohon hubungi pengelola sistem dan sebutkan kode "
    "eksekusi di bawah."
)


def msg_header_not_found(detail):
    return (
        "Judul kolom pada file tidak dapat dikenali. Pastikan sheet pertama "
        "memiliki baris judul yang berisi ID Resp, Desa, RT, Person, lalu "
        f"kolom indikator (X1.1 dan seterusnya). Keterangan sistem: {detail}"
    )


def msg_missing_columns(names):
    return (
        f"File belum lengkap: {len(names)} kolom wajib tidak ditemukan, yaitu "
        f"{name_list(names)}. Pastikan semua kolom tersedia dengan nama yang "
        "sama persis seperti di data master, tanpa kolom kosong atau kolom "
        "asing di tengah deretan kolom, lalu impor kembali."
    )


def msg_indicators_without_questionnaire(codes):
    return (
        "Perhatian: indikator berikut belum memiliki kuesioner aktif sehingga "
        f"kolomnya tidak ikut diimpor: {name_list(codes)}. Tambahkan "
        "Questionnaire untuk indikator tersebut bila datanya ingin dipakai."
    )


def failure_message(execution):
    """Kalimat penjelasan untuk eksekusi yang berhenti."""
    summary = execution.output_summary or {}
    return summary.get("user_message") or MSG_UNEXPECTED


def group_by_rule(rejections):
    """{rule: set(nomor baris)} untuk satu kumpulan RejectionLog."""
    groups = {}
    for r in rejections:
        groups.setdefault(r.rule, set()).add(r.source_row)
    return groups


def examples(rejections, limit=MAX_EXAMPLES):
    """Contoh: 'Baris 5, kolom X1.1: <alasan>'."""
    lines = []
    seen = set()
    for r in rejections:
        key = (r.source_row, r.column_name, r.rule)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"Baris {r.source_row}, kolom {r.column_name}: {r.reason}")
        if len(lines) == limit:
            break
    return lines


def bullet_lines(items):
    return "\n".join(f"- {item}" for item in items)


def result_messages(execution):
    """
    Pesan hasil untuk pengguna: list of (level, teks) dengan level
    "success" | "warning" | "error".
    """

    from .models import ExecutionLog

    code = f"Kode eksekusi: {execution.execution_id}."
    summary = execution.output_summary or {}
    out = []

    if execution.status != ExecutionLog.STATUS_SUCCESS:
        kind = (
            "Struktur file tidak sesuai"
            if execution.status == ExecutionLog.STATUS_FAILED_SCHEMA
            else "Proses terhenti"
        )
        out.append((
            "error",
            f"Impor dibatalkan. {kind}. {failure_message(execution)} "
            f"Tidak ada data yang disimpan. {code}",
        ))
        return out

    rejected_p1 = execution.rejections.filter(checkpoint="P1")
    p2 = execution.rejections.filter(checkpoint="P2")

    out.append((
        "error" if execution.n_output == 0 and execution.n_input else "success",
        f"Impor selesai. Dari {execution.n_input} baris data, "
        f"{execution.n_output} baris berhasil disimpan"
        + (
            f" dan {execution.n_rejected_p1} baris tidak diproses karena "
            "datanya bermasalah"
            if execution.n_rejected_p1 else ""
        )
        + f". {code}",
    ))

    if execution.n_rejected_p1:
        groups = group_by_rule(rejected_p1)
        parts = [
            f"{len(rows)} baris: {rule_label(rule)}"
            for rule, rows in sorted(groups.items(), key=lambda x: -len(x[1]))
        ]
        out.append((
            "warning",
            f"{execution.n_rejected_p1} baris tidak disimpan karena datanya "
            "perlu diperbaiki di file Excel.\n"
            "Ringkasan masalah:\n" + bullet_lines(parts) + "\n"
            "Contoh:\n" + bullet_lines(examples(rejected_p1)),
        ))
        out.append((
            "warning",
            "Sistem tidak memperbaiki atau mengisi data secara otomatis. "
            "Perbaiki baris yang bermasalah di file Excel, lalu impor ulang.",
        ))

    if execution.n_lost:
        lost = p2.filter(rule="record_not_stored")
        out.append((
            "error",
            f"{execution.n_lost} baris sudah lolos pemeriksaan tetapi gagal "
            "tersimpan di database.\nContoh:\n"
            + bullet_lines(examples(lost)),
        ))

    if execution.n_rejected_p2:
        out.append((
            "error",
            f"{execution.n_rejected_p2} baris tersimpan dengan isi yang "
            "berbeda dari file, sehingga dikeluarkan dari perhitungan.\n"
            "Contoh:\n" + bullet_lines(
                examples(p2.exclude(rule="record_not_stored"))
            ),
        ))

    missing_q = summary.get("indicators_without_questionnaire")
    if missing_q:
        out.append(("warning", msg_indicators_without_questionnaire(missing_q)))

    skipped = summary.get("n_skipped_rows")
    if skipped:
        out.append((
            "warning",
            f"{skipped} baris dilewati oleh proses penyimpanan. Detailnya "
            "dapat dilihat pada log eksekusi.",
        ))

    return out
