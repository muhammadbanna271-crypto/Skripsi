import json

import anthropic
import requests
from django.conf import settings
from pydantic import BaseModel
from typing import Literal

from .prompts import EXTRACTION_PROMPT, PROMPT_VERSION


class SLRLLMError(Exception):
    pass


class _ScreeningSchema(BaseModel):
    status: Literal["included", "excluded", "uncertain"]
    reason: str = ""
    confidence: float | None = None
    evidence: str = ""


class _EvidenceItemSchema(BaseModel):
    original_name: str
    normalized_name: str
    evidence: str


class _VariableSchema(_EvidenceItemSchema):
    description: str = ""
    variable_role: str = ""


class _DimensionSchema(_EvidenceItemSchema):
    variable_normalized_name: str


class _IndicatorSchema(_EvidenceItemSchema):
    variable_normalized_name: str
    dimension_normalized_name: str = ""


class _FactorSchema(_EvidenceItemSchema):
    affected_outcome: str
    relationship: str = ""


class _SLROutputSchema(BaseModel):
    screening: _ScreeningSchema
    keywords: list[_EvidenceItemSchema] = []
    variables: list[_VariableSchema] = []
    dimensions: list[_DimensionSchema] = []
    indicators: list[_IndicatorSchema] = []
    factors: list[_FactorSchema] = []


class SLRLLMService:
    """SLR-only structured-output adapter; PRUDENCE remains unchanged."""

    @classmethod
    def is_configured(cls):
        return (
            settings.SLR_LLM_PROVIDER == "gemini" and bool(settings.GEMINI_API_KEY)
        ) or (
            settings.SLR_LLM_PROVIDER == "anthropic" and bool(settings.ANTHROPIC_API_KEY)
        ) or (
            settings.SLR_LLM_PROVIDER == "deepseek" and bool(settings.DEEPSEEK_API_KEY)
        )

    @classmethod
    def validate_connection(cls):
        """Validate Gemini once before a multi-article workflow."""
        if not cls.is_configured():
            raise SLRLLMError("Selected SLR LLM provider is not configured")
        if settings.SLR_LLM_PROVIDER != "gemini":
            return
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            client.models.generate_content(
                model=settings.SLR_LLM_MODEL,
                contents="Return exactly this JSON object: {}",
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
        except Exception as error:
            raise SLRLLMError(f"Gemini preflight failed: {str(error)[:500]}") from error

    @classmethod
    def extract(cls, article):
        content = (article.full_text or article.abstract or "").strip()
        if not content:
            raise SLRLLMError("Article has no abstract or extracted full text")
        payload = f"ARTICLE TITLE: {article.title}\n\nARTICLE CONTENT:\n{content[:settings.SLR_LLM_MAX_INPUT_CHARS]}"
        provider = settings.SLR_LLM_PROVIDER
        if provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise SLRLLMError("GEMINI_API_KEY is not configured")
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                response = client.models.generate_content(
                    model=settings.SLR_LLM_MODEL,
                    contents=f"{EXTRACTION_PROMPT}\n\n{payload}",
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                        response_schema=_SLROutputSchema,
                    ),
                )
                raw = response.text
            except Exception as error:
                raise SLRLLMError(f"Gemini request failed: {str(error)[:500]}") from error
        elif provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise SLRLLMError("ANTHROPIC_API_KEY is not configured")
            response = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY).messages.create(model=settings.SLR_LLM_MODEL, max_tokens=4096, system=EXTRACTION_PROMPT, messages=[{"role": "user", "content": payload}])
            raw = "".join(block.text for block in response.content if block.type == "text")
        elif provider == "deepseek":
            if not settings.DEEPSEEK_API_KEY:
                raise SLRLLMError("DEEPSEEK_API_KEY is not configured")
            response = requests.post("https://api.deepseek.com/chat/completions", headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}", "Content-Type": "application/json"}, json={"model": settings.SLR_LLM_MODEL, "messages": [{"role": "system", "content": EXTRACTION_PROMPT}, {"role": "user", "content": payload}], "response_format": {"type": "json_object"}}, timeout=settings.SLR_HTTP_TIMEOUT_SECONDS)
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
        else:
            raise SLRLLMError("SLR_LLM_PROVIDER must be gemini, anthropic, or deepseek")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise SLRLLMError("LLM returned invalid JSON") from error
        cls._validate(value)
        return value, provider, settings.SLR_LLM_MODEL, PROMPT_VERSION

    @staticmethod
    def _validate(value):
        if not isinstance(value, dict) or not isinstance(value.get("screening"), dict):
            raise SLRLLMError("LLM JSON lacks screening object")
        if value["screening"].get("status") not in {"included", "excluded", "uncertain"}:
            raise SLRLLMError("LLM JSON has invalid screening status")
        for key in ("keywords", "variables", "dimensions", "indicators", "factors"):
            if not isinstance(value.get(key, []), list):
                raise SLRLLMError(f"LLM JSON field {key} must be a list")
