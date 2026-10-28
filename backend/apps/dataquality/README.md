# Data Quality (apps/dataquality)

Lapisan validasi + pencatatan di atas import Excel. Tidak mengubah scoring,
agregasi, TOPSIS, K-Means, master, maupun instrumen.

Alur: `Read Excel -> Schema Gate -> P1 -> Accept/Reject -> Database -> P2 -> agregasi skor existing`

## Command (jalankan dari folder `backend`)

| Tujuan | Command |
|---|---|
| Buat dataset cacat + ground truth | `manage.py dq_inject bersih.xlsx cacat.xlsx truth.json --defect missing_value --seed 42 --count 10` |
| Dataset bersih (kontrol) | `manage.py dq_inject bersih.xlsx kontrol.xlsx truth.json --defect clean --seed 0` |
| Import tervalidasi | `manage.py dq_import cacat.xlsx --survey 1 --ground-truth truth.json --report-dir hasil/` |
| Ekspor satu execution | `manage.py dq_report <execution_id> --output hasil/` |
| Ekspor execution terbaru | `manage.py dq_report --latest --output hasil/` |
| Bandingkan dua execution | `manage.py dq_report <id_B> --output hasil/ --compare-with <id_A>` |

`--defect`: `missing_value`, `wrong_type`, `out_of_range`, `duplicate`
(`--variant row|id|combo`), `missing_column` (`--variant drop|blank`),
`unknown_village`, `clean`.

## Isi folder ekspor

- `report.txt` - ringkasan yang dapat dibaca manusia (mulai dari sini)
- `execution_summary.csv` - satu baris per execution
- `rejection_detail.csv` - semua pelanggaran P1 dan P2 (satu baris per pelanggaran)
- `discrepancy_detail.csv` - subset P2: nilai sumber vs database + tindakan
- `quality_score.csv` - n_checked, n_satisfied, score per checkpoint & dimensi
- `fingerprints.txt` - hash responden / jawaban / skor
- `ground_truth.csv`, `evaluation.csv`, `evaluation_locations.csv` - bila ada ground truth
- `comparison.txt` - bila memakai `--compare-with`

## Aturan penting

- Satuan: completeness & validity = sel; consistency & uniqueness = rekaman.
  `score = n_satisfied / n_checked`; kosong (NULL) bila `n_checked = 0`.
- Duplikat: kemunculan pertama dipertahankan, berikutnya ditolak
  (`related_row` menunjuk baris pertama).
- `delta_n = n_input - (n_output + n_rejected) = n_lost`.
  `n_rejected = n_rejected_p1 + n_rejected_p2`; `n_lost` dicatat terpisah.
- P2 yang menemukan nilai tersimpan berbeda dari sumber: bukti (nilai sumber,
  nilai database, kolom) dicatat lebih dulu, baru rekaman dikeluarkan dari
  tabel Respondent/Response agar tidak ikut skoring
  (`record_action = removed_from_scoring_tables`).
- Domain `Person` belum aktif; isi `DATAQUALITY_ALLOWED_PERSONS` di settings
  bila daftar resmi tersedia. Status tampil di `report.txt`.
- Evaluasi precision/recall memakai deteksi P1; satuan lokasi: cell
  (missing/type/range/unknown village/blank column), row (duplicate),
  column (drop column). `id_resp` pada ground truth = ID sebelum injeksi.
- Fingerprint = keadaan database di akhir execution (seluruh tabel), tanpa
  timestamp/PK. Determinisme: reset DB lalu jalankan ulang; idempotensi:
  upload ulang tanpa reset.
