import logging
import re
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import JobResult

logger = logging.getLogger(__name__)

# Matches [attr] at the end of a selector, e.g. "a[href]" or "div.link[data-url]"
_ATTR_RE = re.compile(r'\[([^\]=]+)\]$')


def scrape(source: dict) -> list[JobResult]:
    resp = requests.get(
        source["url"],
        timeout=15,
        headers={"User-Agent": "JobAlert/1.0"},
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    selectors = source.get("selectors", {})
    container_sel = selectors.get("job_container", "article")
    containers = soup.select(container_sel)

    base_url = source["url"]
    results: list[JobResult] = []
    for el in containers:
        title = _extract(el, selectors.get("title"))
        url   = _extract(el, selectors.get("url"))
        if not title or not url:
            continue
        url = urljoin(base_url, url)  # resolve relative URLs

        results.append(JobResult(
            source_name=source["name"],
            title=title.strip(),
            url=url.strip(),
            company=_extract(el, selectors.get("company")),
            location=_extract(el, selectors.get("location")),
            skills=_extract(el, selectors.get("skills")),
        ))
    return results


def _extract(el, selector: Optional[str]) -> Optional[str]:
    if not selector:
        return None
    m = _ATTR_RE.search(selector)
    if m:
        attr = m.group(1)
        base = selector[:m.start()]
        target = el.select_one(base) if base else el
        if not target:
            return None
        val = target.get(attr)
        return str(val).strip() if val else None
    found = el.select_one(selector)
    return found.get_text(strip=True) if found else None
