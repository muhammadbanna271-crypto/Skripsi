import json

from django.core.management.base import BaseCommand, CommandError

from apps.dataquality.pipeline import ValidatedImportService
from apps.dataquality.reporting import export_execution
from apps.survey.models import Survey


class Command(BaseCommand):
    help = (
        "Import Excel responden lewat Schema Gate, P1, penyimpanan, P2 "
        "dan pipeline existing. Hasil tercatat di ExecutionLog."
    )

    def add_arguments(self, parser):
        parser.add_argument("file")
        parser.add_argument("--survey", type=int, required=True)
        parser.add_argument("--no-scoring", action="store_true")
        parser.add_argument(
            "--ground-truth",
            help="JSON ground truth dari dq_inject; disimpan di execution.",
        )
        parser.add_argument(
            "--report-dir",
            help="Langsung ekspor hasil (dq_report) ke folder ini.",
        )

    def handle(self, *args, **options):
        survey = Survey.objects.filter(pk=options["survey"]).first()
        if survey is None:
            raise CommandError("Survey tidak ditemukan.")

        truth = None
        if options["ground_truth"]:
            with open(options["ground_truth"], encoding="utf-8") as handle:
                truth = json.load(handle)

        execution = ValidatedImportService.run(
            options["file"],
            survey,
            run_scoring=not options["no_scoring"],
            ground_truth=truth,
        )

        self.stdout.write(f"execution_id : {execution.execution_id}")
        self.stdout.write(f"status       : {execution.status}")
        self.stdout.write(
            f"N_input={execution.n_input} diterima(P1)={execution.n_accepted} "
            f"ditolak={execution.n_rejected} (P1={execution.n_rejected_p1}, "
            f"P2={execution.n_rejected_p2}) hilang={execution.n_lost} "
            f"output={execution.n_output} deltaN={execution.delta_n}"
        )
        for score in execution.quality_scores.all():
            self.stdout.write(
                f"  {score.checkpoint} {score.dimension:<12} "
                f"{score.n_satisfied}/{score.n_checked} = {score.score}"
            )
        if execution.error_message:
            self.stdout.write(execution.error_message)

        if options["report_dir"]:
            export_execution(execution, options["report_dir"])
            self.stdout.write(f"report       : {options['report_dir']}")
