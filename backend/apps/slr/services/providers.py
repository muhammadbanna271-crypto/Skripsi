import logging
import time

import requests
from django.conf import settings

from .normalization import normalize_doi, year_from_value

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    pass


class ScholarlyProvider:
    name = ""

    def __init__(self):
        self.session = requests.Session()

    def _get(self, url, *, params=None, headers=None):
        attempts = settings.SLR_HTTP_MAX_RETRIES + 1
        for attempt in range(attempts):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=settings.SLR_HTTP_TIMEOUT_SECONDS,
                )
            except requests.RequestException as error:
                if attempt == attempts - 1:
                    raise ProviderError(str(error)) from error
                time.sleep(settings.SLR_HTTP_BACKOFF_SECONDS * (2 ** attempt))
                continue

            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as error:
                    raise ProviderError("Provider returned invalid JSON") from error
            if response.status_code not in (408, 429, 500, 502, 503, 504):
                raise ProviderError(f"Provider HTTP {response.status_code}: {response.text[:500]}")
            # Do not make a user-facing run wait through a long sequence of
            # 429 retries. Crossref results remain useful and the next run
            # can retry this provider normally.
            if response.status_code == 429:
                raise ProviderError("Provider is temporarily rate-limited (HTTP 429); retry the run later")
            if attempt == attempts - 1:
                raise ProviderError(f"Provider HTTP {response.status_code}")
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else settings.SLR_HTTP_BACKOFF_SECONDS * (2 ** attempt)
            time.sleep(delay)
        raise ProviderError("Provider retry loop ended unexpectedly")


class CrossrefProvider(ScholarlyProvider):
    name = "crossref"
    endpoint = "https://api.crossref.org/works"

    def search(self, query, filters, limit):
        # Crossref's /works route does not support `language` in select.
        params = {
            "query.bibliographic": query,
            "rows": limit,
            "mailto": settings.CROSSREF_MAILTO,
            "select": "DOI,title,author,published-print,published-online,issued,container-title,publisher,abstract,URL,type,link",
        }
        filter_parts = []
        if filters.get("year_from"):
            filter_parts.append(f"from-pub-date:{filters['year_from']}-01-01")
        if filters.get("year_to"):
            filter_parts.append(f"until-pub-date:{filters['year_to']}-12-31")
        if filters.get("publication_types"):
            filter_parts.append("type:" + filters["publication_types"][0])
        if filter_parts:
            params["filter"] = ",".join(filter_parts)
        # Crossref /works uses the public REST API. Do not send or request an
        # API key; `mailto` above is the required polite-pool identifier.
        data = self._get(self.endpoint, params=params)
        return [self.normalize(item) for item in data.get("message", {}).get("items", [])]

    def normalize(self, item):
        authors = [" ".join(part for part in (author.get("given"), author.get("family")) if part) for author in item.get("author", [])]
        dates = item.get("published-print") or item.get("published-online") or item.get("issued") or {}
        date_parts = dates.get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        links = item.get("link") or []
        full_text_url = next((link.get("URL", "") for link in links if link.get("content-type") == "application/pdf"), "")
        return {
            "provider_id": item.get("DOI") or item.get("URL") or item.get("title", [""])[0],
            "doi": normalize_doi(item.get("DOI")),
            "title": (item.get("title") or [""])[0], "authors": authors,
            "publication_year": year_from_value(year),
            "journal": (item.get("container-title") or [""])[0],
            "publisher": item.get("publisher") or "",
            "abstract": item.get("abstract") or "", "article_url": item.get("URL") or "",
            "full_text_url": full_text_url, "publication_type": item.get("type") or "",
            "language": item.get("language") or "", "raw_payload": item,
        }


class SemanticScholarProvider(ScholarlyProvider):
    name = "semantic_scholar"
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"

    def search(self, query, filters, limit):
        params = {"query": query, "limit": limit, "fields": "paperId,title,authors,year,venue,abstract,externalIds,url,publicationTypes,openAccessPdf"}
        data = self._get(self.endpoint, params=params)
        records = [self.normalize(item) for item in data.get("data", [])]
        return [record for record in records if self._within_year_range(record, filters)]

    @staticmethod
    def _within_year_range(record, filters):
        year = record.get("publication_year")
        return not year or (not filters.get("year_from") or year >= int(filters["year_from"])) and (not filters.get("year_to") or year <= int(filters["year_to"]))

    def normalize(self, item):
        external_ids = item.get("externalIds") or {}
        pdf = item.get("openAccessPdf") or {}
        return {
            "provider_id": item.get("paperId") or external_ids.get("DOI") or item.get("url") or item.get("title", ""),
            "doi": normalize_doi(external_ids.get("DOI")), "title": item.get("title") or "",
            "authors": [author.get("name", "") for author in item.get("authors", [])],
            "publication_year": year_from_value(item.get("year")), "journal": item.get("venue") or "",
            "publisher": "",
            "abstract": item.get("abstract") or "", "article_url": item.get("url") or "",
            "full_text_url": pdf.get("url") or "", "publication_type": ", ".join(item.get("publicationTypes") or []),
            "language": "", "raw_payload": item,
        }


PROVIDERS = {CrossrefProvider.name: CrossrefProvider, SemanticScholarProvider.name: SemanticScholarProvider}
