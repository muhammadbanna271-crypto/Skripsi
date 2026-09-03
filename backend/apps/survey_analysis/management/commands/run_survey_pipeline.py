"""Jalankan pipeline analisis survei dari CLI.

Contoh:
    python manage.py run_survey_pipeline
    python manage.py run_survey_pipeline --sem-engine semopy --random-state 42
"""

from django.core.management.base import BaseCommand

from apps.survey_analysis.pipeline.runner import run_pipeline


class Command(BaseCommand):
    help = "Jalankan pipeline analisis survei (SEM → LCA → ML → SHAP)."

    def add_arguments(self, parser):
        parser.add_argument("--sem-engine", default="semopy", choices=["semopy", "lavaan"])
        parser.add_argument("--sem-estimator", default="ULS")
        parser.add_argument("--random-state", type=int, default=42)

    def handle(self, *args, **options):
        config = {
            "sem_engine": options["sem_engine"],
            "sem_estimator": options["sem_estimator"],
            "random_state": options["random_state"],
        }
        self.stdout.write("Menjalankan pipeline... (bisa beberapa menit)")
        out = run_pipeline(config)
        for h in out["state"].history:
            self.stdout.write(f"  {h['stage']}: {h['status']}"
                              + (f" — {h['message']}" if h["message"] else ""))
        if out.get("report_path"):
            self.stdout.write(self.style.SUCCESS(f"Report: {out['report_path']}"))
