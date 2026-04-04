"""
Local dashboard entry point.

The scraper/notifier runs separately on the VM (notify.py).
This process only serves the Flask dashboard, which reads job history
from the Telegram channel via Telethon.

Usage:
    python run.py

First-time setup: run  python auth_telethon.py  before this.
Dashboard:        http://localhost:5001
"""
import logging
import sys

from app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

app = create_app()

if __name__ == "__main__":
    print("Dashboard → http://localhost:5001")
    app.run(host="127.0.0.1", port=5001, debug=True, use_reloader=False)
