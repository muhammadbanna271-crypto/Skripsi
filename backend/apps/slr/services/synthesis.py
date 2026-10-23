from django.db.models import Count

from apps.slr.models import Evidence, Factor, Synthesis, Variable


class SLRSynthesisService:
    """Counts are calculated from persisted evidence, never by an LLM."""

    @classmethod
    def rebuild(cls):
        Synthesis.objects.all().delete()
        cls._build(Variable.objects, "variable")
        cls._build(Factor.objects, "factor")

    @classmethod
    def _build(cls, manager, concept_type):
        groups = manager.values("normalized_name").annotate(study_count=Count("article", distinct=True)).order_by("normalized_name")
        for group in groups:
            items = manager.filter(normalized_name=group["normalized_name"])
            synthesis = Synthesis.objects.create(normalized_concept=group["normalized_name"], concept_type=concept_type, supporting_study_count=group["study_count"], synthesis_text=f"{group['normalized_name']} was supported by {group['study_count']} study/studies.")
            synthesis.supporting_articles.set(items.values_list("article_id", flat=True).distinct())
            synthesis.evidence_references.set(items.values_list("evidence_id", flat=True).distinct())
