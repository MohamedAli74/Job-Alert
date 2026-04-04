"""
Reads job alerts from a private Telegram channel using Telethon (user account API).

The channel acts as the database — the VM bot posts every job there.
The local dashboard reads backwards through the channel until it hits
the [*LOADED*] marker sent by the previous dashboard load, collecting
the "new" jobs in between.

On each dashboard load, a new [*LOADED*] marker is posted (via the bot),
so the next load knows exactly where to stop.

One-time setup required: run  python auth_telethon.py  to create job_alert.session.
"""
import logging
import os
from typing import Optional

from telethon.sync import TelegramClient
from telethon.tl.types import MessageEntityTextUrl

from notifier import LOADED_MARKER
from scrapers.base import infer_role_type

logger = logging.getLogger(__name__)

SESSION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "job_alert")


def _make_client(cfg: dict) -> TelegramClient:
    tg = cfg["telegram"]
    return TelegramClient(SESSION_PATH, int(tg["api_id"]), tg["api_hash"])


def fetch_jobs(cfg: dict, limit: int = 500) -> tuple[list[dict], list[dict]]:
    """
    Read up to `limit` messages from the channel newest-first.

    Returns (new_jobs, prev_jobs) where:
    - new_jobs:  jobs posted after the most recent [*LOADED*] marker
    - prev_jobs: jobs posted between the two most recent [*LOADED*] markers
    """
    channel_id = cfg["telegram"]["chat_id"]

    new_messages = []
    old_messages = []
    loaded_found = False
    with _make_client(cfg) as client:
        for msg in client.iter_messages(channel_id, limit=limit):
            if not loaded_found:
                if msg.raw_text and msg.raw_text.strip() == LOADED_MARKER:
                    loaded_found = True
                else:
                    new_messages.append(msg)
            else:
                if msg.raw_text and msg.raw_text.strip() != LOADED_MARKER:
                    old_messages.append(msg)

    new_jobs  = [_parse(m) for m in reversed(new_messages) if _parse(m)]
    prev_jobs = [_parse(m) for m in reversed(old_messages) if _parse(m)]

    return new_jobs, prev_jobs


# ── Message parser ────────────────────────────────────────────────────────────

def _parse(msg) -> Optional[dict]:
    """
    Parse a Telethon message into a job dict.
    Returns None if the message is not a job alert.

    Expected raw_text format (HTML tags stripped by Telethon):
        New Job Alert

        {title}
        🏢 {company}  📍 {location}
        🛠 {skills}
        📦 {source_name}

        View Job →
    """
    raw = msg.raw_text or ""
    if "New Job Alert" not in raw:
        return None

    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if len(lines) < 2:
        return None

    # lines[0] = "New Job Alert", lines[1] = title
    title = lines[1]
    company = location = skills = source_name = ""

    for line in lines[2:]:
        if "🏢" in line:
            body = line.replace("🏢", "").strip()
            if "📍" in body:
                parts = body.split("📍", 1)
                company  = parts[0].strip()
                location = parts[1].strip()
            else:
                company = body
        elif "🛠" in line:
            val = line.replace("🛠", "").strip()
            skills = val if val != "N/A" else ""
        elif "📦" in line:
            source_name = line.replace("📦", "").strip()

    url = _get_url(msg)
    if not url or not title:
        return None

    return {
        "title":       title,
        "company":     company,
        "location":    location,
        "url":         url,
        "skills":      skills,
        "source_name": source_name,
        "role_type":   infer_role_type(title) or "",
        "date_found":  msg.date.strftime("%b %d, %Y") if msg.date else "",
    }


def _get_url(msg) -> str:
    """Extract the hyperlink URL from a Telethon message entity."""
    if not msg.entities:
        return ""
    for ent in msg.entities:
        if isinstance(ent, MessageEntityTextUrl):
            return ent.url
    return ""
