import json

from django.core.management.base import BaseCommand, CommandError

from apps.dataquality.models import ExecutionLog
from apps.dataquality.reporting import export_execution


class Command(BaseCommand):
    help = (
        "Ekspor hasil satu execution ke folder (CSV + report.txt + "
        "fingerprints.txt) agar dapat diperiksa tanpa database."
    )

    def add_arguments(self, parser):
        parser.add_argument("execution_id", nargs="?")
        parser.add_argument("--latest", action="store_true")
        parser.add_argument("--output", required=True)
        parser.add_argument(
            "--xlsx",
            action="store_true",
            help="Tulis juga laporan_dq_<execution_id>.xlsx di folder output.",
        )
        parser.add_argument(
            "--ground-truth",
            help="JSON ground truth (menimpa yang tersimpan di execution).",
        )
        parser.add_argument(
            "--compare-with",
            help="execution_id pembanding (determinisme/idempotensi).",
        )

    def handle(self, *args, **options):
        if bool(options["execution_id"]) == bool(options["latest"]):
            raise CommandError(
                "Berikan tepat satu: <execution_id> atau --latest."
            )

        if options["latest"]:
            execution = ExecutionLog.objects.order_by("-started_at", "-id").first()
        else:
            execution = ExecutionLog.objects.filter(
                execution_id=options["execution_id"]
            ).first()

        if execution is None:
            raise CommandError("Execution tidak ditemukan.")

        other = None
        if options["compare_with"]:
            other = ExecutionLog.objects.filter(
                execution_id=options["compare_with"]
            ).first()
            if other is None:
                raise CommandError("Execution pembanding tidak ditemukan.")

        truth = None
        if options["ground_truth"]:
            with open(options["ground_truth"], encoding="utf-8") as handle:
                truth = json.load(handle)

        paths = export_execution(
            execution, options["output"], truth=truth, compare_with=other
        )

        if options["xlsx"]:
            import os

            from apps.dataquality.reporting import build_workbook

            paths["xlsx"] = os.path.join(
                options["output"], f"laporan_dq_{execution.execution_id}.xlsx"
            )
            build_workbook(execution).save(paths["xlsx"])

        self.stdout.write(f"execution_id: {execution.execution_id}")
        for name, path in paths.items():
            self.stdout.write(f"  {name:<28} {path}")
