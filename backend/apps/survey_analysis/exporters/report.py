"""Generator final report (Markdown)."""

from apps.survey_analysis.config import settings as cfg
from apps.survey_analysis.config import model_config
from apps.survey_analysis.exporters import exporter


def _fmt(v, nd=3):
    if v is None:
        return "—"
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return str(v)


def generate_report(state, results):
    lines = []
    add = lines.append

    add("# Laporan Analisis Survei — Pipeline SEM/LCA/ML/SHAP")
    add("")

    # ---------- Data quality ----------
    add("## 1. Kualitas Data")
    val = results.get("validation", {}).get("summary", {})
    add(f"- Responden: **{results.get('n_respondents', '—')}**")
    add(f"- Item Likert: **{results.get('n_items', '—')}**")
    add(f"- Nilai invalid (di luar skala): {val.get('n_invalid_values', '—')}")
    add(f"- Missing cells: {val.get('n_missing_cells', '—')}")
    add(f"- Item near-zero variance (flag): {val.get('n_near_zero_items', '—')}")
    rev = val.get("reverse_coded", {})
    add(f"- Reverse-coded: {'dikonfirmasi: ' + str(rev.get('items')) if rev.get('confirmed') else 'belum dikonfirmasi (tidak di-recode otomatis)'}")
    add("")

    # ---------- Reliability ----------
    add("## 2. Reliabilitas (Cronbach's Alpha & McDonald's Omega)")
    rel = results.get("reliability", {})
    if rel:
        df = rel.get("results")
        add("| Konstruk | Items | Alpha | Omega | Status |")
        add("|---|---|---|---|---|")
        for _, row in df.iterrows():
            add(f"| {row['construct']} {row['name']} | {row['n_items']} | {_fmt(row['cronbach_alpha'])} | {_fmt(row['omega'])} | {row['status']} |")
    add("")

    # ---------- CFA ----------
    add("## 3. CFA (Measurement Model)")
    cfa = results.get("cfa", {})
    if cfa:
        fi = cfa.get("fit_indices", {})
        add(f"- Estimator: {cfa.get('estimator', '—')}")
        add("| CFI | TLI | RMSEA | SRMR | Chi² (df) | p |")
        add("|---|---|---|---|---|---|")
        add(f"| {_fmt(fi.get('cfi'))} | {_fmt(fi.get('tli'))} | {_fmt(fi.get('rmsea'))} | {_fmt(fi.get('srmr'))} | {_fmt(fi.get('chi2'), 1)} ({_fmt(fi.get('dof'), 0)}) | {_fmt(fi.get('p_value'), 4)} |")
    add("")

    # ---------- SEM ----------
    add("## 4. SEM (Structural Model)")
    sem = results.get("sem", {})
    if sem:
        fi = sem.get("fit_indices", {})
        add(f"| CFI | TLI | RMSEA | Chi² (df) |")
        add("|---|---|---|---|")
        add(f"| {_fmt(fi.get('cfi'))} | {_fmt(fi.get('tli'))} | {_fmt(fi.get('rmsea'))} | {_fmt(fi.get('chi2'), 1)} ({_fmt(fi.get('dof'), 0)}) |")
        paths = sem.get("path_coefficients")
        if paths is not None and not paths.empty:
            add("")
            add("**Path coefficients (24 jalur):**")
            add("| Target | Source | Estimate | Std | p |")
            add("|---|---|---|---|---|")
            for _, r in paths.iterrows():
                add(f"| {r['lhs']} | {r['rhs']} | {_fmt(r['est'], 2)} | {_fmt(r['standardized'], 2)} | {_fmt(r['p_value'], 4)} |")
    add("")

    # ---------- LCA ----------
    add("## 5. LCA (Latent Class Analysis)")
    lca = results.get("lca", {})
    if lca:
        comp = lca.get("comparison")
        add("| Kelas | AIC | BIC | LogLik | Entropy | Min class % |")
        add("|---|---|---|---|---|---|")
        for _, r in comp.iterrows():
            add(f"| {int(r['classes'])} | {_fmt(r['aic'], 1)} | {_fmt(r['bic'], 1)} | {_fmt(r['log_likelihood'], 3)} | {_fmt(r['entropy'])} | {_fmt(r['min_class_pct'], 1)} |")
        sel = lca.get("selection", {})
        add(f"\n**Terpilih: {sel.get('selected')} kelas.** {sel.get('reason')}")
        if sel.get("review_required"):
            add("⚠️ REVIEW REQUIRED — keputusan jumlah kelas perlu verifikasi substantif.")
        diag = lca.get("diagnostics")
        if diag is not None and not diag.empty:
            add("")
            add("| Kelas | Size | % | Ave posterior prob |")
            add("|---|---|---|---|")
            for _, r in diag.iterrows():
                add(f"| {int(r['class'])} | {int(r['class_size'])} | {r['class_percentage']}% | {r['average_posterior_probability']} |")
    add("")

    # ---------- ML ----------
    add("## 6. Surrogate Machine Learning")
    ml = results.get("ml", {})
    if ml:
        add("| Model | Accuracy | Macro F1 | Best params |")
        add("|---|---|---|---|")
        for name, r in ml.get("results", {}).items():
            add(f"| {name} | {_fmt(r['accuracy'])} | {_fmt(r['macro_f1'])} | {r.get('best_params')} |")
    add("")

    # ---------- SHAP ----------
    add("## 7. SHAP (Feature Importance)")
    shap = results.get("shap", {})
    if shap:
        summ = shap.get("summary")
        if summ is not None and not summ.empty:
            add("| Rank | Item | Mean \\|SHAP\\| | Direction | Most affected class |")
            add("|---|---|---|---|---|")
            for _, r in summ.head(10).iterrows():
                add(f"| {int(r['rank'])} | {r['feature']} | {_fmt(r['mean_abs_shap'])} | {r['dominant_direction']} | {r['most_affected_class']} |")
    add("")

    # ---------- Kesimpulan ----------
    add("## 8. Kesimpulan")
    add("> SHAP dan ML bersifat **asosiatif/deskriptif**, BUKAN kausal.")
    add("")
    add("- Temuan statistik (reliabilitas & CFA) — lihat bagian 2–3.")
    add("- Temuan segmentasi (LCA) — lihat bagian 5.")
    add("- Temuan ML (surrogate) — lihat bagian 6.")
    add("- Interpretasi SHAP — lihat bagian 7.")
    add("")

    content = "\n".join(lines)
    exporter._ensure_dirs()
    path = cfg.OUTPUT_DIR / "reports" / "final_report.md"
    path.write_text(content, encoding="utf-8")
    return path
