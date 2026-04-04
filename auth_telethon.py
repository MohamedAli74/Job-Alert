"""
One-time Telethon authentication helper.

Run this ONCE on your local machine to generate job_alert.session:

    python auth_telethon.py

You will be prompted for your phone number and the confirmation code
Telegram sends you. After that, job_alert.session is saved and all
future dashboard loads authenticate silently.

Prerequisites:
  1. Get your api_id and api_hash from https://my.telegram.org
     (Log in → API Development Tools → Create app)
  2. Fill them into config.yaml under telegram.api_id and telegram.api_hash
  3. Make sure your bot is an admin in the private channel you set as chat_id
"""
import os
import sys
import yaml

SESSION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "job_alert")
CFG_PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

if not os.path.exists(CFG_PATH):
    print("ERROR: config.yaml not found.")
    print("Copy config.example.yaml to config.yaml and fill in your values first.")
    sys.exit(1)

with open(CFG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

tg = cfg.get("telegram", {})
api_id   = tg.get("api_id")
api_hash = tg.get("api_hash")

if not api_id or not api_hash or "YOUR_" in str(api_id) or "YOUR_" in str(api_hash):
    print("ERROR: telegram.api_id and telegram.api_hash are not set in config.yaml.")
    print("Get them from https://my.telegram.org → API Development Tools")
    sys.exit(1)

# Import here so the script fails early if telethon isn't installed
from telethon.sync import TelegramClient  # noqa: E402

print("Starting Telethon authentication...")
print("You will receive a confirmation code via Telegram.\n")

with TelegramClient(SESSION_PATH, int(api_id), api_hash) as client:
    client.start()
    me = client.get_me()
    print(f"\nAuthenticated as: {me.first_name} (@{me.username})")
    print(f"Session file saved: {SESSION_PATH}.session")
    print("\nYou can now run:  python run.py")
