import logging
import httpx

logger = logging.getLogger(__name__)

LOADED_MARKER = "[*LOADED*]"


def send_telegram(job, bot_token: str, chat_id: str) -> bool:
    """Send a single job alert via the Telegram Bot HTTP API.
    Returns True on success, False on any error (never raises)."""
    text = (
        f"<b>New Job Alert</b>\n\n"
        f"<b>{_esc(job.title)}</b>\n"
        f"🏢 {_esc(job.company or 'N/A')}  📍 {_esc(job.location or 'Remote')}\n"
        f"🛠 {_esc(job.skills or 'N/A')}\n"
        f"📦 <i>{_esc(job.source_name)}</i>\n\n"
        f'<a href="{job.url}">View Job →</a>'
    )
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("Telegram API %s: %s", resp.status_code, resp.text[:200])
            return False
        return True
    except Exception:
        logger.exception("Failed to send Telegram notification")
        return False


def send_loaded_marker(bot_token: str, chat_id: str) -> bool:
    """Send a [*LOADED*] boundary marker to the channel.
    Called by the local dashboard on each load so the next load knows
    where to stop when reading backwards through channel history."""
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": LOADED_MARKER},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        logger.exception("Failed to send LOADED marker")
        return False


def _esc(text: str) -> str:
    """Minimal HTML escaping for Telegram HTML parse mode."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
