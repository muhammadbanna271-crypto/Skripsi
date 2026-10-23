import re
import unicodedata
from datetime import datetime


def normalize_doi(value):
    if not value:
        return ""
    value = value.strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    return value.removeprefix("doi:").strip().rstrip(".,;)")


def normalize_title(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", value.casefold())).strip()


def year_from_value(value):
    if isinstance(value, int):
        return value if 1000 <= value <= 9999 else None
    if not value:
        return None
    match = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", str(value))
    return int(match.group(1)) if match else None


def iso_now():
    return datetime.utcnow().isoformat() + "Z"
