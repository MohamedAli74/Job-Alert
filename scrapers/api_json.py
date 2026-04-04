import logging
from typing import Optional

import requests

from .base import JobResult

logger = logging.getLogger(__name__)


def scrape(source: dict) -> list[JobResult]:
    resp = requests.get(
        source["url"],
        timeout=15,
        headers={"User-Agent": "JobAlert/1.0"},
    )
    resp.raise_for_status()
    data = resp.json()

    # Handle both top-level list and {"jobs": [...]} / {"data": [...]} wrappers
    if isinstance(data, dict):
        for key in ("jobs", "data", "results", "positions", "offers"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            # Fallback: take the first list value
            data = next((v for v in data.values() if isinstance(v, list)), [])

    fields = source.get("fields", {})
    title_key = fields.get("title", "title")
    url_key   = fields.get("url", "url")

    results: list[JobResult] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = item.get(title_key)
        if not title:
            # Skip metadata rows (RemoteOK: first item is {"legal": "..."})
            continue
        url = item.get(url_key)
        if not url:
            continue

        # Skills: may be a list (e.g. RemoteOK "tags") — join to string
        skills_raw = item.get(fields["skills"]) if fields.get("skills") else None
        if isinstance(skills_raw, list):
            skills: Optional[str] = ", ".join(str(s) for s in skills_raw if s) or None
        elif isinstance(skills_raw, str) and skills_raw.strip():
            skills = skills_raw.strip()
        else:
            skills = None

        results.append(JobResult(
            source_name=source["name"],
            title=str(title).strip(),
            url=str(url).strip(),
            company=_get(item, fields.get("company", "")),
            location=_get(item, fields.get("location", "")),
            skills=skills,
        ))
    return results


def _get(item: dict, key: str) -> Optional[str]:
    if not key:
        return None
    val = item.get(key)
    return str(val).strip() if val else None
