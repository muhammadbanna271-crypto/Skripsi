import io
import re

import requests
from django.conf import settings

from apps.slr.models import Article


class ArticleTextService:
    """Retrieve only a URL already advertised as publicly accessible."""

    @classmethod
    def fetch(cls, article):
        if not article.full_text_url:
            article.text_status, article.text_error = "unavailable", "No public full-text URL"
            article.save(update_fields=["text_status", "text_error", "updated_at"])
            return article
        try:
            response = requests.get(article.full_text_url, timeout=settings.SLR_HTTP_TIMEOUT_SECONDS)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if "pdf" in content_type or article.full_text_url.lower().split("?")[0].endswith(".pdf"):
                text = cls._pdf_text(response.content)
            else:
                text = cls._html_text(response.text)
            if not text.strip():
                raise ValueError("No readable text was found")
            article.full_text, article.text_status, article.text_error = text[:2_000_000], "available", ""
            article.access_status = Article.ACCESS_FULL_TEXT
        except Exception as error:
            article.text_status, article.text_error = "parse_failed", str(error)[:2000]
        article.save(update_fields=["full_text", "text_status", "text_error", "access_status", "updated_at"])
        return article

    @staticmethod
    def _html_text(value):
        value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
        return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", value)).strip()

    @staticmethod
    def _pdf_text(content):
        try:
            from pypdf import PdfReader
        except ImportError as error:
            raise RuntimeError("pypdf is not installed") from error
        return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
