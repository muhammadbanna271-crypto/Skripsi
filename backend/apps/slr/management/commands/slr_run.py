from django.core.management.base import BaseCommand, CommandError

from apps.slr.models import SLRRun
from apps.slr.services import SLRRetrievalPipeline


class Command(BaseCommand):
    help = "Retrieve, normalize, filter, and persist literature for an existing SLR run."

    def add_arguments(self, parser):
        parser.add_argument("run_id")
        parser.add_argument("--max-results", type=int, default=50)
        parser.add_argument("--fetch-text", action="store_true")
        parser.add_argument("--extract", action="store_true")
        parser.add_argument("--synthesize", action="store_true")

    def handle(self, *args, **options):
        if options["max_results"] < 1 or options["max_results"] > 1000:
            raise CommandError("--max-results must be between 1 and 1000")
        try:
            run = SLRRun.objects.get(pk=options["run_id"])
        except (SLRRun.DoesNotExist, ValueError) as error:
            raise CommandError("SLR run was not found") from error
        result = SLRRetrievalPipeline(run, limit=options["max_results"]).execute()
        from apps.slr.services.keywords import SLRKeywordService
        SLRKeywordService.rebuild_for_run(result)
        if options["fetch_text"]:
            from apps.slr.models import ArticleSource
            from apps.slr.services.text import ArticleTextService
            for source in ArticleSource.objects.filter(run=result, article__full_text_url__gt="").select_related("article"):
                ArticleTextService.fetch(source.article)
        if options["extract"]:
            from apps.slr.models import ArticleSource
            from apps.slr.services.processing import SLRArticleProcessor
            from apps.slr.services.llm import SLRLLMService
            if SLRLLMService.is_configured():
                seen = set()
                for source in ArticleSource.objects.filter(run=result, article__isnull=False).select_related("article"):
                    if source.article_id not in seen:
                        SLRArticleProcessor.process(source.article)
                        seen.add(source.article_id)
            else:
                self.stdout.write(self.style.WARNING("Skipping AI extraction: configure GEMINI_API_KEY, DEEPSEEK_API_KEY, or ANTHROPIC_API_KEY first."))
        if options["synthesize"]:
            from apps.slr.services import SLRSynthesisService
            SLRSynthesisService.rebuild()
        self.stdout.write(self.style.SUCCESS(f"SLR run {result.pk}: {result.status}; accepted={result.accepted_count}, duplicates={result.duplicate_count}, errors={result.error_count}"))
