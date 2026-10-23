import logging

from django.db import transaction
from django.utils import timezone

from apps.slr.models import Article, ArticleSource, SLRRun

from .normalization import normalize_doi, normalize_title
from .providers import PROVIDERS, ProviderError

logger = logging.getLogger(__name__)


class SLRRetrievalPipeline:
    """Deterministic retrieval and persistence; it never calls an LLM."""

    def __init__(self, run, limit=50):
        self.run = run
        self.limit = limit

    def execute(self):
        self.run.status = SLRRun.STATUS_RUNNING
        self.run.started_at = timezone.now()
        self.run.finished_at = None
        self.run.error_summary = ""
        self.run.retrieved_count = self.run.accepted_count = self.run.duplicate_count = self.run.error_count = 0
        self.run.save()
        errors = []
        for provider_name in self.run.providers:
            provider_class = PROVIDERS.get(provider_name)
            if not provider_class:
                errors.append(f"Unsupported provider: {provider_name}")
                self.run.error_count += 1
                continue
            try:
                records = provider_class().search(self.run.search_query, self.run.filters, self.limit)
            except ProviderError as error:
                logger.warning("SLR provider %s failed for run %s: %s", provider_name, self.run.pk, error)
                errors.append(f"{provider_name}: {error}")
                self.run.error_count += 1
                continue
            for record in records:
                self.run.retrieved_count += 1
                try:
                    accepted, duplicate = self._persist_record(provider_name, record)
                    self.run.accepted_count += int(accepted)
                    self.run.duplicate_count += int(duplicate)
                except Exception as error:  # retain other provider records on a malformed item
                    logger.exception("SLR record persistence failed")
                    errors.append(f"{provider_name} record: {error}")
                    self.run.error_count += 1
        # One provider may be temporarily rate-limited while the other has
        # still produced a valid, traceable candidate set. Preserve that
        # usable run as completed and expose the provider problem as a
        # warning in error_summary rather than discarding Crossref results.
        # A rerun can legitimately find only already-stored articles. Those
        # records remain valid candidates and must not make the run fail.
        self.run.status = SLRRun.STATUS_COMPLETED if self.run.retrieved_count else SLRRun.STATUS_FAILED
        self.run.error_summary = "\n".join(errors)
        self.run.finished_at = timezone.now()
        self.run.execution_metadata = {**self.run.execution_metadata, "last_limit": self.limit}
        self.run.save()
        return self.run

    def _persist_record(self, provider_name, record):
        title = record.get("title", "").strip()
        provider_id = str(record.get("provider_id") or "").strip()
        if not title or not provider_id:
            raise ValueError("Provider record lacks a title or stable identifier")
        if not self._matches_filters(record):
            ArticleSource.objects.update_or_create(
                run=self.run, provider=provider_name, provider_article_id=provider_id,
                defaults={"source_query": self.run.search_query, "status": ArticleSource.FILTERED, "raw_payload": record.get("raw_payload", {})},
            )
            return False, False
        doi = normalize_doi(record.get("doi")) or None
        normalized_title = normalize_title(title)
        with transaction.atomic():
            article, created, duplicate = self._find_or_create(doi, normalized_title, record)
            ArticleSource.objects.update_or_create(
                run=self.run, provider=provider_name, provider_article_id=provider_id,
                defaults={"article": article, "source_query": self.run.search_query, "status": ArticleSource.RETRIEVED, "raw_payload": record.get("raw_payload", {})},
            )
            self._refresh_source_database(article)
        # "accepted" means this candidate passed deterministic filtering and
        # is linked to the run, whether it created a new Article or matched a
        # previously retrieved one. `duplicate` reports the latter case.
        return True, duplicate

    def _find_or_create(self, doi, normalized_title, record):
        article = Article.objects.filter(doi=doi).first() if doi else None
        if article is None:
            article = Article.objects.filter(normalized_title=normalized_title, publication_year=record.get("publication_year")).first()
        if article is not None:
            self._merge_article(article, record, doi)
            return article, False, True
        access_status = Article.ACCESS_FULL_TEXT if record.get("full_text_url") else Article.ACCESS_ABSTRACT if record.get("abstract") else Article.ACCESS_METADATA_ONLY
        article = Article.objects.create(
            doi=doi, title=record["title"].strip(), normalized_title=normalized_title,
            source_database="",
            authors=record.get("authors") or [], publication_year=record.get("publication_year"),
            journal=record.get("journal") or "", publisher=record.get("publisher") or "", abstract=record.get("abstract") or "",
            article_url=record.get("article_url") or "", full_text_url=record.get("full_text_url") or "",
            publication_type=record.get("publication_type") or "", language=record.get("language") or "",
            access_status=access_status, metadata_payload=record.get("raw_payload") or {}, last_retrieved_at=timezone.now(),
        )
        return article, True, False

    def _merge_article(self, article, record, doi):
        fields = {"last_retrieved_at": timezone.now()}
        for field, value in (("doi", doi), ("abstract", record.get("abstract")), ("full_text_url", record.get("full_text_url")), ("article_url", record.get("article_url")), ("journal", record.get("journal")), ("publisher", record.get("publisher")), ("language", record.get("language"))):
            if value and not getattr(article, field):
                fields[field] = value
        if fields.get("full_text_url"):
            fields["access_status"] = Article.ACCESS_FULL_TEXT
        elif fields.get("abstract") and article.access_status == Article.ACCESS_METADATA_ONLY:
            fields["access_status"] = Article.ACCESS_ABSTRACT
        for field, value in fields.items():
            setattr(article, field, value)
        article.save(update_fields=list(fields) + ["updated_at"])

    @staticmethod
    def _refresh_source_database(article):
        providers = set(article.sources.values_list("provider", flat=True))
        if {"semantic_scholar", "crossref"}.issubset(providers):
            source_database = "both"
        elif "semantic_scholar" in providers:
            source_database = "semantic_scholar"
        elif "crossref" in providers:
            source_database = "crossref"
        else:
            source_database = ""
        if article.source_database != source_database:
            article.source_database = source_database
            article.save(update_fields=["source_database", "updated_at"])

    def _matches_filters(self, record):
        filters = self.run.filters or {}
        year = record.get("publication_year")
        if filters.get("year_from") and year and year < int(filters["year_from"]):
            return False
        if filters.get("year_to") and year and year > int(filters["year_to"]):
            return False
        allowed_types = {value.casefold() for value in filters.get("publication_types", [])}
        if allowed_types and record.get("publication_type", "").casefold() not in allowed_types:
            return False
        allowed_languages = {value.casefold() for value in filters.get("languages", [])}
        if allowed_languages and record.get("language") and record["language"].casefold() not in allowed_languages:
            return False
        return True
