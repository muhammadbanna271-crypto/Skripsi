from django.core.management.base import BaseCommand

from apps.dataquality.injection import DEFECT_TYPES, inject, write_clean
from apps.dataquality.reader import registered_village_codes


class Command(BaseCommand):
    help = (
        "Buat dataset cacat (satu jenis cacat) + ground truth JSON dari "
        "workbook bersih. Seed dicatat di ground truth."
    )

    def add_arguments(self, parser):
        parser.add_argument("source")
        parser.add_argument("out")
        parser.add_argument("truth")
        parser.add_argument("--defect", choices=DEFECT_TYPES + ("clean",), required=True)
        parser.add_argument("--seed", type=int, required=True)
        parser.add_argument("--count", type=int, default=10)
        parser.add_argument("--variant", default=None)

    def handle(self, *args, **options):
        if options["defect"] == "clean":
            truth = write_clean(
                options["source"], options["out"], options["truth"],
                seed=options["seed"],
            )
            self.stdout.write(f"dataset bersih (kontrol) -> {options['out']}")
            return

        truth = inject(
            options["source"],
            options["out"],
            options["truth"],
            options["defect"],
            seed=options["seed"],
            count=options["count"],
            variant=options["variant"],
            known_village_codes=registered_village_codes(),
        )
        self.stdout.write(
            f"{truth['count']} cacat '{truth['defect_type']}' "
            f"(seed={truth['seed']}) -> {options['out']}"
        )
