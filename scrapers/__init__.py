import logging

from .base import JobResult, infer_role_type
from . import api_json, rss, html

logger = logging.getLogger(__name__)

SCRAPERS = {
    "api_json":    api_json.scrape,
    "rss":         rss.scrape,
    "html_scrape": html.scrape,
}

__all__ = ["scrape_source", "JobResult", "infer_role_type"]


def scrape_source(source: dict) -> list[JobResult]:
    """Dispatch to the correct scraper. Returns [] on any error so one broken
    source never blocks the others."""
    scraper = SCRAPERS.get(source.get("type", ""))
    if not scraper:
        logger.warning(
            "Unknown source type '%s' for source '%s'",
            source.get("type"), source.get("name"),
        )
        return []
    try:
        results = scraper(source)
        logger.info("%-20s → %d job(s)", source.get("name", "?"), len(results))
        return results
    except Exception:
        logger.exception("Scraper failed for source '%s'", source.get("name"))
        return []
