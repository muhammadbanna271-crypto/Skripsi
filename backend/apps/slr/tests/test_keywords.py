from django.test import TestCase

from apps.slr.models import Article, ArticleSource, Keyword, SLRRun
from apps.slr.services.keywords import SLRKeywordService
from apps.slr.services.normalization import normalize_title


class SLRKeywordServiceTest(TestCase):
    def setUp(self):
        self.run = SLRRun.objects.create(
            topic="Tourism village development",
            search_query="Tourism village development",
            providers=["crossref", "semantic_scholar"],
        )
        for index, title in enumerate((
            "Factors for Tourism Village Development",
            "Tourism Village Development and Community Participation",
        )):
            article = Article.objects.create(
                doi=f"10.1000/test{index}", title=title,
                normalized_title=normalize_title(title), journal=f"Journal {index}",
            )
            ArticleSource.objects.create(
                run=self.run, article=article, provider="crossref",
                provider_article_id=f"test-{index}", raw_payload={},
            )

    def test_creates_traceable_repeated_title_keywords(self):
        SLRKeywordService.rebuild_for_run(self.run)

        records = Keyword.objects.filter(normalized_name="tourism village development")
        self.assertEqual(records.count(), 2)
        self.assertTrue(all(record.evidence.evidence_type == "article_title_keyword" for record in records))

    def test_rebuild_does_not_duplicate_keywords(self):
        SLRKeywordService.rebuild_for_run(self.run)
        first_count = Keyword.objects.count()
        SLRKeywordService.rebuild_for_run(self.run)

        self.assertEqual(Keyword.objects.count(), first_count)
