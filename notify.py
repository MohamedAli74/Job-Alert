"""
VM daemon — optimized for 1GB RAM (Oracle Cloud Free).

No ORM, no scheduler library. Uses stdlib sqlite3 for dedup and a plain
sleep loop for scheduling — nothing that doesn't need to be in memory is.

Usage:
    python notify.py
"""
import logging
import os
import signal
import sqlite3
import sys
import time

import yaml

from config_loader import load_preferences
from notifier import send_telegram
from scrapers import scrape_source, infer_role_type
from scrapers.base import JobResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH  = os.path.join(_BASE_DIR, "seen_urls.db")

# ── Dedup DB (stdlib sqlite3 — no ORM overhead) ───────────────────────────────

def _db() -> sqlite3.Connection:
    con = sqlite3.connect(_DB_PATH)
    con.execute(
        "CREATE TABLE IF NOT EXISTS seen_urls "
        "(url TEXT PRIMARY KEY)"
    )
    con.commit()
    return con


def _is_new(con: sqlite3.Connection, url: str) -> bool:
    """Return True and mark as seen if the URL has not been seen before."""
    try:
        con.execute("INSERT INTO seen_urls (url) VALUES (?)", (url,))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


# ── Precompile filter sets (once per cycle, not per job) ──────────────────────

class _Filter:
    __slots__ = ("locations", "remote_ok", "excludes", "includes", "field_kws")

    def __init__(self, prefs: dict) -> None:
        seniority     = prefs.get("seniority", {})
        self.locations = frozenset(l.lower() for l in prefs.get("locations", []))
        self.remote_ok = "remote" in self.locations
        self.excludes  = frozenset(k.lower() for k in seniority.get("exclude", []))
        self.includes  = frozenset(k.lower() for k in seniority.get("include", []))
        self.field_kws = frozenset(k.lower() for k in prefs.get("field_keywords", []))

    def passes(self, job: JobResult) -> bool:
        t = job.title.lower()
        loc = (job.location or "").lower()

        if self.locations:
            if not (any(l in loc for l in self.locations) or
                    (self.remote_ok and not loc.strip())):
                return False

        if self.excludes and any(ex in t for ex in self.excludes):
            return False

        if self.includes and not any(kw in t for kw in self.includes):
            return False

        if self.field_kws and not any(kw in t for kw in self.field_kws):
            return False

        return True


# ── Scrape cycle ──────────────────────────────────────────────────────────────

def run_cycle(cfg: dict) -> None:
    tg        = cfg["telegram"]
    bot_token = tg.get("bot_token", "")
    chat_id   = tg.get("chat_id", "")
    notify_ok = bool(
        bot_token and chat_id
        and "YOUR_" not in bot_token
        and "YOUR_" not in chat_id
    )

    filt     = _Filter(load_preferences())
    new_count = 0

    with _db() as con:
        for source in cfg.get("sources", []):
            for r in scrape_source(source):
                if not filt.passes(r):
                    continue
                if not _is_new(con, r.url):
                    continue
                if notify_ok:
                    send_telegram(r, bot_token, chat_id)
                new_count += 1

    if new_count:
        logger.info("Cycle: %d new job(s)%s",
                    new_count, " sent" if notify_ok else "")
    else:
        logger.info("Cycle: no new jobs")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    cfg_path = os.path.join(_BASE_DIR, "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    interval = int(cfg.get("scheduler", {}).get("interval_minutes", 60)) * 60

    # Graceful shutdown on SIGTERM (systemd sends this on `systemctl stop`)
    running = True
    def _stop(sig, frame):
        nonlocal running
        logger.info("Shutting down...")
        running = False
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT,  _stop)

    logger.info("Running initial scrape cycle...")
    run_cycle(cfg)
    logger.info("Notifier running — every %d min.", interval // 60)

    # Plain sleep loop — no scheduler library in memory
    deadline = time.monotonic() + interval
    while running:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            run_cycle(cfg)
            deadline = time.monotonic() + interval
        else:
            time.sleep(min(remaining, 30))  # wake up every 30s to check SIGTERM


if __name__ == "__main__":
    main()
