# Job Alert

A personal job alert system that scrapes multiple job boards, filters postings by role and seniority, and delivers matches to a private Telegram channel.

> **Archived.** This monorepo has been split into two focused repos:
> [`job-alert-vm`](https://github.com/MohamedAli74/job-alert-vm) — the scraper/notifier daemon  
> [`job-alert-dashboard`](https://github.com/MohamedAli74/job-alert-dashboard) — the local web dashboard

---

## How it works

```
┌─────────────────────────────────────┐        ┌──────────────────────┐
│  vm/notify.py  (background daemon)  │        │  Telegram channel    │
│                                     │  bot   │  (private, acts as   │
│  Every 60 min:                      │───────>│   the job database)  │
│  1. Scrape job boards               │        └──────────┬───────────┘
│  2. Filter by preferences           │                   │ Telethon
│  3. Dedup via SQLite                │        ┌──────────v───────────┐
│  4. Send new matches via bot        │        │  dashboard/run.py    │
└─────────────────────────────────────┘        │  (localhost:5001)    │
                                               │                      │
                                               │  Browse, filter,     │
                                               │  configure           │
                                               └──────────────────────┘
```

The Telegram channel acts as a persistent, append-only log. The dashboard reads backwards through it on each load, stopping at a `[*LOADED*]` marker it placed on the previous visit — everything above the marker is "new", everything below is history.

---

## Components

### `vm/` — Scraper daemon

Runs as a background process (added to Windows startup via `add_to_startup.bat`).

| File | Purpose |
|------|---------|
| `notify.py` | Main loop — scrape → filter → dedup → notify |
| `scrapers/linkedin.py` | LinkedIn guest API (no auth, supports `f_TPR` recency filter) |
| `scrapers/api_json.py` | Generic JSON API scraper (RemoteOK, etc.) |
| `scrapers/rss.py` | RSS/Atom feed scraper (HN Jobs, etc.) |
| `scrapers/html.py` | Generic HTML scraper with CSS selector config |
| `scrapers/indeed.py` | Indeed scraper |
| `config.yaml` | Sources, Telegram credentials, scheduler interval *(gitignored)* |
| `configuration/preferences.yaml` | Filter rules — seniority, field keywords, locations *(gitignored)* |
| `seen_urls.db` | SQLite dedup database *(gitignored)* |

### `dashboard/` — Local web dashboard

Flask app served on `http://localhost:5001`. Requires a one-time Telethon auth (`python auth_telethon.py`) to create a user session for reading the channel.

| File | Purpose |
|------|---------|
| `run.py` | Entry point |
| `app.py` | Flask routes — dashboard, `/api/jobs`, `/configure/*` |
| `telegram_reader.py` | Reads job history from Telegram channel via Telethon |
| `config.yaml` | Telegram credentials for Telethon *(gitignored)* |
| `configuration/preferences.yaml` | Shared preferences (same file as vm reads) *(gitignored)* |
| `job_alert.session` | Telethon user session *(gitignored)* |

---

## Setup

### 1. Telegram credentials

You need two things:
- A **bot token** from [@BotFather](https://t.me/BotFather) — the VM uses this to post jobs
- An **API ID + hash** from [my.telegram.org](https://my.telegram.org) — the dashboard uses these to read via Telethon

Create a private channel, add your bot as an admin with posting rights, and note the channel's chat ID (use [@userinfobot](https://t.me/userinfobot)).

### 2. VM notifier

```bash
cd vm
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copy `config.example.yaml` to `config.yaml` and fill in your credentials and sources. Then run:

```bash
# Start manually
start_notifier.bat

# Or add to Windows startup (runs automatically at login)
add_to_startup.bat
```

### 3. Dashboard

```bash
cd dashboard
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# One-time: authenticate Telethon with your Telegram account
python auth_telethon.py

# Start the dashboard
python run.py
```

Open `http://localhost:5001`.

---

## Configuration

Both components share `configuration/preferences.yaml` for filter rules:

```yaml
seniority:
  include: [intern, junior, graduate, entry level]
  exclude: [senior, lead, principal, manager, director]

field_keywords: [software, engineer, developer, backend, frontend, devops, data, ml, ai, cyber]

locations: [remote, israel, tel aviv, haifa]
```

Job sources are configured in `vm/config.yaml`. The LinkedIn scraper supports multiple keyword queries and a `hours_posted` filter to only surface recent listings:

```yaml
sources:
- name: LinkedIn Israel - intern
  type: linkedin
  keywords: software intern
  location: Israel
  hours_posted: 24       # only jobs posted in the last 24 hours
```

Supported source types: `linkedin`, `indeed`, `api_json`, `rss`, `html_scrape`.

All configuration can also be edited through the dashboard's `/configure` page.

---

## Architecture notes

- **No scheduler library** — the VM uses a plain `sleep` loop to minimize memory use (targets Oracle Cloud's 1 GB free-tier VM)
- **No ORM** — deduplication is raw `sqlite3` with a single `seen_urls` table
- **Telegram as the database** — the channel's message history is the job store; the dashboard needs no local DB of its own
- **LinkedIn pagination limit** — the unauthenticated guest API returns at most ~10 results per query and does not paginate beyond the first page; the workaround is running multiple keyword queries

---

## License

MIT
