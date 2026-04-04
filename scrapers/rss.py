import logging
from typing import Optional

import feedparser

from .base import JobResult

logger = logging.getLogger(__name__)


def scrape(source: dict) -> list[JobResult]:
    feed = feedparser.parse(source["url"])
    fields = source.get("fields", {})

    title_key = fields.get("title", "title")
    url_key   = fields.get("url", "link")

    results: list[JobResult] = []
    for entry in feed.entries:
        title = getattr(entry, title_key, None)
        url   = getattr(entry, url_key, None)
        if not title or not url:
            continue

        results.append(JobResult(
            source_name=source["name"],
            title=str(title).strip(),
            url=str(url).strip(),
            company=_get(entry, fields.get("company")),
            location=_get(entry, fields.get("location")),
            skills=_get(entry, fields.get("skills")),
        ))
    return results


def _get(entry, key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    val = getattr(entry, key, None)
    return str(val).strip() if val else None
