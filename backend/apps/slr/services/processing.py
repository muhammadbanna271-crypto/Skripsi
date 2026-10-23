from django.db import transaction
from django.utils import timezone
import re

from apps.slr.models import Dimension, Evidence, Extraction, Factor, Indicator, Keyword, ScreeningResult, Variable

from .llm import SLRLLMError, SLRLLMService
from .normalization import normalize_title


class SLRArticleProcessor:
    @classmethod
    def process(cls, article):
        extraction = Extraction.objects.create(article=article)
        try:
            data, provider, model, prompt_version = SLRLLMService.extract(article)
            with transaction.atomic():
                cls._save(article, extraction, data)
                extraction.status, extraction.validation_status = Extraction.COMPLETED, "validated"
                extraction.provider, extraction.model_name, extraction.prompt_version, extraction.processed_at = provider, model, prompt_version, timezone.now()
                extraction.save()
        except SLRLLMError as error:
            extraction.status, extraction.validation_status, extraction.summary = Extraction.UNCERTAIN, "invalid", str(error)
            extraction.processed_at = timezone.now()
            extraction.save()
        return extraction

    @classmethod
    def _save(cls, article, extraction, data):
        screening = data["screening"]
        ScreeningResult.objects.update_or_create(article=article, defaults={"status": screening["status"], "confidence": screening.get("confidence") or None, "reason": screening.get("reason", ""), "evidence": screening.get("evidence", ""), "screened_at": timezone.now()})
        if screening["status"] != ScreeningResult.INCLUDED:
            return
        for item in data.get("keywords", []):
            Keyword.objects.create(article=article, extraction=extraction, original_name=item["original_name"], normalized_name=normalize_title(item.get("normalized_name") or item["original_name"]), evidence=cls._evidence(article, extraction, item))
        variables = {}
        for item in data.get("variables", []):
            evidence = cls._evidence(article, extraction, item)
            variable = Variable.objects.create(article=article, extraction=extraction, original_name=item["original_name"], normalized_name=normalize_title(item.get("normalized_name") or item["original_name"]), description=item.get("description", ""), variable_role=item.get("variable_role", ""), evidence=evidence)
            variables[variable.normalized_name] = variable
        dimensions = {}
        for item in data.get("dimensions", []):
            variable = variables.get(normalize_title(item.get("variable_normalized_name")))
            if variable:
                evidence = cls._evidence(article, extraction, item)
                dimension = Dimension.objects.create(article=article, variable=variable, original_name=item["original_name"], normalized_name=normalize_title(item.get("normalized_name") or item["original_name"]), evidence=evidence)
                dimensions[dimension.normalized_name] = dimension
        for item in data.get("indicators", []):
            variable = variables.get(normalize_title(item.get("variable_normalized_name")))
            if variable:
                Indicator.objects.create(article=article, variable=variable, dimension=dimensions.get(normalize_title(item.get("dimension_normalized_name"))), original_name=item["original_name"], normalized_name=normalize_title(item.get("normalized_name") or item["original_name"]), evidence=cls._evidence(article, extraction, item))
        for item in data.get("factors", []):
            Factor.objects.create(article=article, extraction=extraction, original_name=item["original_name"], normalized_name=normalize_title(item.get("normalized_name") or item["original_name"]), affected_outcome=item["affected_outcome"], relationship=item.get("relationship", ""), evidence=cls._evidence(article, extraction, item))

    @staticmethod
    def _evidence(article, extraction, item):
        evidence = (item.get("evidence") or "").strip()
        content = article.full_text or article.abstract
        normalized_evidence = re.sub(r"\s+", " ", evidence).strip().casefold()
        normalized_content = re.sub(r"\s+", " ", content).strip().casefold()
        if not evidence or normalized_evidence not in normalized_content:
            raise SLRLLMError("Extraction evidence is absent from article content")
        return Evidence.objects.create(article=article, extraction=extraction, snippet=evidence, evidence_type="llm_extraction")
