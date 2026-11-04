import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def canonicalize(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")])
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def fingerprint(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def record_fingerprint(title: str, body: str) -> str:
    """Fingerprint of the body; falls back to the title so empty bodies stay distinct."""
    return fingerprint(body if body.strip() else title)
