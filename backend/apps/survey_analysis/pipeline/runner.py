"""Runner pipeline: orkestrasi seluruh tahap + STOP conditions + export.

Alur: VALIDATION → RELIABILITY → CFA → SEM → LCA → ML → SHAP → COMPLETED.
STOP conditions (tidak dipaksa lanjut):
- Reliabilitas: alpha/omega < 0.60 -> STOP.
- CFA measurement: CFI/TLI/RMSEA gagal -> STOP.
- Surrogate ML: accuracy < 0.80 -> STOP (sebelum SHAP).

Semua hasil ditulis ke outputs/ (CSV/JSON) + final report markdown.
"""

from apps.survey_analysis.config import settings as cfg
from apps.survey_analysis.config import model_config
from apps.survey_analysis.data.loader import load_dataset
from apps.survey_analysis.validation.validation import run_validation
from apps.survey_analysis.reliability.reliability import run_reliability
from apps.survey_analysis.cfa import get_sem_engine
from apps.survey_analysis.cfa.diagnostics import (
    evaluate_fit,
    evaluate_loadings,
    compute_effects,
    mediation_summary,
)
from apps.survey_analysis.lca.runner import (
    fit_models as lca_fit_models,
    select_classes,
    classification_diagnostics,
    class_profiles,
)
from apps.survey_analysis.ml.runner import run_surrogate_ml
from apps.survey_analysis.shap.explainer import explain, summary_table
from apps.survey_analysis.exporters import exporter
from apps.survey_analysis.pipeline.state import (
    PipelineState,
    VALIDATION, RELIABILITY, CFA, SEM, LCA, ML, SHAP, COMPLETED,
)


def _definite_fit_fail(fit_indices):
    """True bila ada kriteria fit yang PASTI gagal (bukan None/unknown)."""
    for c in evaluate_fit(fit_indices):
        if c["passed"] is False:
            return True
    return False


def run_pipeline(config=None):
    """Jalankan seluruh pipeline. Return dict {state, results, report_path}."""
    config = config or {}
    sem_engine = config.get("sem_engine", "semopy")
    sem_estimator = config.get("sem_estimator", "ULS")
    ml_engines = config.get("ml_engines", ("xgboost", "random_forest"))
    random_state = config.get("random_state", cfg.RANDOM_STATE)
    class_range = config.get("class_range", cfg.LCA_CLASS_RANGE)

    state = PipelineState()
    results = {}

    # ---- Data ----
    ds = load_dataset()
    matrix = ds["matrix"]
    results["n_respondents"] = int(matrix.shape[0])
    results["n_items"] = int(matrix.shape[1])

    # ---- 1. Validation ----
    val = run_validation(matrix)
    results["validation"] = val
    exporter.write_json(val["summary"], "validation", "validation_summary.json")
    exporter.write_csv(val["missing"]["per_item"], "validation", "missing_values.csv")
    exporter.write_csv(val["variance"], "validation", "variance_check.csv")
    exporter.write_csv(val["normality"], "validation", "normality.csv")
    state.log(VALIDATION, "PASSED")

    # ---- 2. Reliability (STOP) ----
    rel = run_reliability(matrix)
    results["reliability"] = rel
    exporter.write_csv(rel["results"], "reliability", "reliability_results.csv")
    if not rel["passed"]:
        state.stop(RELIABILITY, rel["message"])
        exporter.write_json({"state": state.stages_summary()}, "reports", "pipeline_state.json")
        return {"state": state, "results": results, "report_path": None}
    state.log(RELIABILITY, "PASSED")

    # ---- 3. CFA (measurement) + 4. SEM (structural) ----
    engine = get_sem_engine(sem_engine)
    # 3a. CFA measurement (fit check).
    engine.fit(matrix, measurement_only=True, estimator=sem_estimator)
    cfa_fit = engine.fit_indices()
    loadings = engine.factor_loadings()
    results["cfa"] = {
        "fit_indices": cfa_fit,
        "loadings": loadings,
        "estimator": engine.estimator_label,
    }
    exporter.write_json(cfa_fit, "cfa", "fit_indices.json")
    exporter.write_csv(evaluate_loadings(loadings), "cfa", "factor_loadings.csv")

    if _definite_fit_fail(cfa_fit):
        state.stop(CFA, "CFA tidak memenuhi kriteria fit (CFI/TLI/RMSEA).")
        exporter.write_json({"state": state.stages_summary()}, "reports", "pipeline_state.json")
        return {"state": state, "results": results, "report_path": None}
    state.log(CFA, "PASSED")

    # 3b. SEM structural (path coefficients + effects).
    engine.fit(matrix, measurement_only=False, estimator=sem_estimator)
    sem_fit = engine.fit_indices()
    paths = engine.path_coefficients()
    effects = compute_effects(paths)
    results["sem"] = {
        "fit_indices": sem_fit,
        "path_coefficients": paths,
        "effects": effects,
    }
    exporter.write_json(sem_fit, "cfa", "sem_fit_indices.json")
    exporter.write_csv(paths, "cfa", "path_coefficients.csv")
    exporter.write_csv(effects["direct"], "cfa", "direct_effects.csv")
    exporter.write_csv(effects["indirect"], "cfa", "indirect_effects.csv")
    exporter.write_csv(effects["total"], "cfa", "total_effects.csv")
    state.log(SEM, "PASSED" if not _definite_fit_fail(sem_fit) else "POOR_FIT")

    # ---- 5. LCA ----
    comparison, lca_models = lca_fit_models(
        matrix, class_range=class_range, random_state=random_state
    )
    selection = select_classes(comparison)
    best = lca_models[selection["selected"]]
    class_labels = best.predict_class(matrix).values.astype(int)
    diag, entropy = classification_diagnostics(best, matrix)
    profiles = class_profiles(best, matrix)
    results["lca"] = {
        "comparison": comparison,
        "selection": selection,
        "diagnostics": diag,
        "entropy": entropy,
        "class_labels": class_labels,
    }
    exporter.write_csv(comparison, "lca", "model_comparison.csv")
    exporter.write_json(selection, "lca", "selection.json")
    exporter.write_csv(diag, "lca", "classification_diagnostics.csv")
    exporter.write_csv(best.item_probabilities(), "lca", "conditional_probabilities.csv")
    exporter.write_json(profiles, "lca", "class_profiles.json")
    state.log(LCA, "PASSED")

    # ---- 6. ML (STOP sebelum SHAP) ----
    ml = run_surrogate_ml(
        matrix, class_labels, engines=ml_engines, random_state=random_state
    )
    results["ml"] = ml
    for name, r in ml["results"].items():
        exporter.write_json(
            {k: v for k, v in r.items() if k != "model"},
            "ml", f"metrics_{name}.json",
        )
        exporter.write_csv(r["confusion_matrix"], "ml", f"confusion_matrix_{name}.csv")

    primary = ml["results"].get(ml_engines[0]) or next(iter(ml["results"].values()))
    if primary["accuracy"] < cfg.ML_ACCURACY_MIN:
        state.stop(ML, f"Accuracy surrogate {primary['accuracy']:.3f} < {cfg.ML_ACCURACY_MIN}.")
        exporter.write_json({"state": state.stages_summary()}, "reports", "pipeline_state.json")
        return {"state": state, "results": results, "report_path": None}
    state.log(ML, "PASSED")

    # ---- 7. SHAP ----
    xgb_model = ml["results"].get("xgboost", {}).get("model")
    if xgb_model is not None:
        sh = explain(xgb_model, ml["X_test"], ml["feature_names"])
        summary = summary_table(sh["shap_values"], ml["feature_names"])
        results["shap"] = {"summary": summary}
        exporter.write_csv(summary, "shap", "feature_importance.csv")
    state.log(SHAP, "PASSED")

    # ---- 8. Report ----
    from apps.survey_analysis.exporters.report import generate_report
    report_path = generate_report(state, results)

    exporter.write_json({"state": state.stages_summary()}, "reports", "pipeline_state.json")
    state.log(COMPLETED, "COMPLETED")
    return {"state": state, "results": results, "report_path": report_path}
