import re
from collections import defaultdict

from apps.slr.models import Evidence, Keyword

from .normalization import normalize_title


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "into", "is", "of", "on", "or", "the", "to", "with",
    "an", "dan", "atau", "bagi", "dalam", "dari", "di", "ke", "oleh", "pada", "untuk", "yang", "terhadap", "studi", "study", "analysis", "case",
}


class SLRKeywordService:
    """Build a transparent pre-agent keyword landscape from article titles.

    Every row retains the exact title as evidence, so these are explicitly
    title-derived SLR keywords—not fabricated author keywords or LLM output.
    """

    @classmethod
    def rebuild_for_run(cls, run):
        articles = list({source.article_id: source.article for source in run.article_sources.filter(article__isnull=False).select_related("article")}.values())
        # Remove the prior title-derived representation for this run's papers.
        old_keywords = Keyword.objects.filter(article__in=articles, evidence__evidence_type="article_title_keyword")
        old_evidence_ids = list(old_keywords.values_list("evidence_id", flat=True))
        old_keywords.delete()
        Evidence.objects.filter(pk__in=old_evidence_ids, evidence_type="article_title_keyword").delete()

        phrases = defaultdict(dict)
        for article in articles:
            title = article.title.strip()
            tokens = [token for token in re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", title.casefold()) if token not in STOP_WORDS]
            for size in (1, 2, 3):
                for index in range(len(tokens) - size + 1):
                    phrase = " ".join(tokens[index:index + size])
                    if any(token in STOP_WORDS for token in phrase.split()):
                        continue
                    phrases[phrase][article.pk] = title

        # Use concepts repeated by separate papers. If a very small result
        # set has no repeated phrase, show its most meaningful title terms.
        candidates = [(phrase, supporting) for phrase, supporting in phrases.items() if len(supporting) >= 2]
        if not candidates:
            candidates = [(phrase, supporting) for phrase, supporting in phrases.items() if len(phrase.split()) >= 1]
        candidates.sort(key=lambda item: (-len(item[1]), -len(item[0].split()), item[0]))
        for phrase, supporting in candidates[:20]:
            for article_id, title in supporting.items():
                evidence = Evidence.objects.create(article_id=article_id, snippet=title, source_location="title", evidence_type="article_title_keyword")
                Keyword.objects.create(article_id=article_id, original_name=phrase, normalized_name=normalize_title(phrase), evidence=evidence)
