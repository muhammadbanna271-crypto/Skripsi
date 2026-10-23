from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.slr.models import Article, ArticleSource, SLRRun
from apps.slr.services.pipeline import SLRRetrievalPipeline
from apps.slr.services.providers import CrossrefProvider, SemanticScholarProvider


@override_settings(CROSSREF_MAILTO="gracyellas2005@student.ub.ac.id")
class CrossrefProviderTest(TestCase):
    def test_crossref_uses_polite_pool_mailto_without_api_key(self):
        provider = CrossrefProvider()
        with patch.object(provider, "_get", return_value={"message": {"items": []}}) as request:
            provider.search("tourism village", {}, 10)

        _, kwargs = request.call_args
        self.assertEqual(kwargs["params"]["mailto"], "gracyellas2005@student.ub.ac.id")
        self.assertNotIn("headers", kwargs)

    def test_crossref_maps_publisher_and_doi(self):
        record = CrossrefProvider().normalize({
            "DOI": "10.1234/Example.2024.001",
            "title": ["Tourism Village Development"],
            "author": [{"given": "Ayu", "family": "Putri"}],
            "issued": {"date-parts": [[2024]]},
            "container-title": ["Journal of Tourism"],
            "publisher": "Example Publisher",
            "URL": "https://doi.org/10.1234/Example.2024.001",
        })

        self.assertEqual(record["doi"], "10.1234/example.2024.001")
        self.assertEqual(record["publisher"], "Example Publisher")


class SemanticScholarProviderTest(TestCase):
    def test_existing_semantic_search_query_shape_is_unchanged(self):
        provider = SemanticScholarProvider()
        with patch.object(provider, "_get", return_value={"data": []}) as request:
            provider.search("tourism village", {}, 10)

        _, kwargs = request.call_args
        self.assertEqual(kwargs["params"]["query"], "tourism village")
        self.assertEqual(kwargs["params"]["limit"], 10)
        self.assertIn("externalIds", kwargs["params"]["fields"])
        self.assertNotIn("headers", kwargs)


class MergeDeduplicationTest(TestCase):
    def setUp(self):
        self.run = SLRRun.objects.create(
            topic="Tourism village",
            search_query="Tourism village",
            providers=["semantic_scholar", "crossref"],
        )
        self.pipeline = SLRRetrievalPipeline(self.run)

    def test_doi_merge_preserves_one_article_and_marks_both_sources(self):
        crossref_record = {
            "provider_id": "10.1234/example", "doi": "10.1234/example",
            "title": "Tourism Village Development", "authors": ["Ayu Putri"],
            "publication_year": 2024, "journal": "Tourism Journal",
            "publisher": "Example Publisher", "abstract": "", "article_url": "",
            "full_text_url": "", "publication_type": "journal-article",
            "language": "", "raw_payload": {},
        }
        semantic_record = {
            **crossref_record, "provider_id": "semantic-paper-id",
            "publisher": "", "abstract": "An abstract.",
        }

        self.pipeline._persist_record("crossref", crossref_record)
        self.pipeline._persist_record("semantic_scholar", semantic_record)

        article = Article.objects.get()
        self.assertEqual(Article.objects.count(), 1)
        self.assertEqual(article.doi, "10.1234/example")
        self.assertEqual(article.publisher, "Example Publisher")
        self.assertEqual(article.source_database, "both")
        self.assertEqual(ArticleSource.objects.filter(article=article).count(), 2)

    def test_title_and_year_merge_when_doi_is_unavailable(self):
        record = {
            "provider_id": "crossref-no-doi", "doi": "",
            "title": "Tourism Village Development", "authors": [],
            "publication_year": 2024, "journal": "", "publisher": "",
            "abstract": "", "article_url": "", "full_text_url": "",
            "publication_type": "", "language": "", "raw_payload": {},
        }
        self.pipeline._persist_record("crossref", record)
        self.pipeline._persist_record("semantic_scholar", {**record, "provider_id": "semantic-no-doi"})

        self.assertEqual(Article.objects.count(), 1)
        self.assertEqual(Article.objects.get().source_database, "both")
