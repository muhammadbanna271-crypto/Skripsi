import logging
from threading import Lock

from django.db import close_old_connections
from django.utils import timezone

from apps.slr.models import ArticleSource, Extraction, SLRRun

from .pipeline import SLRRetrievalPipeline
from .keywords import SLRKeywordService
from .processing import SLRArticleProcessor
from .llm import SLRLLMService
from .synthesis import SLRSynthesisService
from .text import ArticleTextService

logger = logging.getLogger(__name__)

# SQLite permits one writer. Each browser click creates a separate daemon
# thread, so serialize workflows in this local deployment. A future queue
# worker can reuse run_slr_workflow without changing its behavior.
_WORKFLOW_LOCK = Lock()


def run_slr_workflow(run_id, max_results=50):
    """Background-safe orchestration for a configured run.

    This is deliberately bounded and records every failure. A future queue
    worker can call this same function without changing the web UI.
    """
    close_old_connections()
    try:
        with _WORKFLOW_LOCK:
            run = SLRRun.objects.get(pk=run_id)
            result = SLRRetrievalPipeline(run, limit=max_results).execute()
            SLRKeywordService.rebuild_for_run(result)
            seen = set()
            if SLRLLMService.is_configured():
                try:
                    SLRLLMService.validate_connection()
                except Exception as error:
                    result.execution_metadata = {**result.execution_metadata, "extraction_status": "provider_preflight_failed"}
                    result.error_summary = "\n".join(filter(None, [result.error_summary, str(error)]))
                    result.save(update_fields=["execution_metadata", "error_summary", "updated_at"])
                else:
                    for source in ArticleSource.objects.filter(run=result, article__isnull=False).select_related("article"):
                        if source.article_id in seen:
                            continue
                        seen.add(source.article_id)
                        if Extraction.objects.filter(article=source.article, status=Extraction.COMPLETED).exists():
                            continue
                        if source.article.full_text_url:
                            ArticleTextService.fetch(source.article)
                        SLRArticleProcessor.process(source.article)
                    SLRSynthesisService.rebuild()
            else:
                result.execution_metadata = {**result.execution_metadata, "extraction_status": "waiting_for_llm_key"}
                result.save(update_fields=["execution_metadata", "updated_at"])
    except Exception as error:
        logger.exception("SLR workflow failed for run %s", run_id)
        SLRRun.objects.filter(pk=run_id).update(status=SLRRun.STATUS_FAILED, finished_at=timezone.now(), error_summary=f"Workflow failure: {error}")
    finally:
        close_old_connections()
