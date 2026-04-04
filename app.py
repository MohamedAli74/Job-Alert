import logging
import os

from flask import Flask, jsonify, redirect, render_template, request, url_for

from config_loader import (
    is_placeholder, load_config, load_preferences,
    save_config, save_preferences,
)
from notifier import send_loaded_marker
from telegram_reader import fetch_jobs

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_job_cache: list[dict] = []


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )
    app.secret_key = "job-alert-local-only"
    if test_config:
        app.config.update(test_config)

    app.config["JOB_ALERT_CONFIG"] = load_config()

    # ── Dashboard ──────────────────────────────────────────────────────────────

    @app.route("/")
    def dashboard():
        global _job_cache
        cfg_  = app.config["JOB_ALERT_CONFIG"]
        tg    = cfg_.get("telegram", {})
        prefs = load_preferences()

        try:
            new_jobs, prev_jobs = fetch_jobs(cfg_)
        except Exception as exc:
            logger.exception("Failed to fetch jobs from Telegram")
            return render_template("setup_error.html", error=str(exc)), 500

        _job_cache = new_jobs + prev_jobs

        bot_token = tg.get("bot_token", "")
        chat_id   = tg.get("chat_id", "")
        if not is_placeholder(bot_token) and not is_placeholder(chat_id):
            send_loaded_marker(bot_token, chat_id)

        return render_template(
            "dashboard.html",
            new_jobs=new_jobs,
            prev_jobs=prev_jobs,
            new_count=len(new_jobs),
            total=len(_job_cache),
            role_filters=prefs.get("dashboard", {}).get("role_filters", []),
            skill_filters=prefs.get("dashboard", {}).get("skill_filters", []),
        )

    @app.route("/api/jobs")
    def api_jobs():
        role  = request.args.get("role", "")
        skill = request.args.get("skill", "").lower()
        jobs  = _job_cache
        if role:
            jobs = [j for j in jobs if j.get("role_type") == role]
        if skill:
            jobs = [j for j in jobs if skill in (j.get("skills") or "").lower()]
        return jsonify(jobs)

    # ── Configure — GET ────────────────────────────────────────────────────────

    @app.route("/configure")
    def configure():
        cfg   = app.config["JOB_ALERT_CONFIG"]
        prefs = load_preferences()
        tg    = cfg.get("telegram", {})

        # Build masked status for each secret — never expose real values to the template
        secrets = {
            "bot_token": _mask(tg.get("bot_token")),
            "chat_id":   _mask(tg.get("chat_id")),
            "api_id":    _mask(tg.get("api_id")),
            "api_hash":  _mask(tg.get("api_hash")),
        }

        return render_template(
            "configure.html",
            secrets=secrets,
            interval=cfg.get("scheduler", {}).get("interval_minutes", 60),
            sources=cfg.get("sources", []),
            prefs=prefs,
        )

    # ── Configure — Secrets (modal form POST) ──────────────────────────────────

    @app.route("/configure/secret", methods=["POST"])
    def configure_secret():
        """Update a single secret field in config.yaml."""
        key   = request.form.get("key", "")     # e.g. "telegram.bot_token"
        value = request.form.get("value", "").strip()
        if key and value:
            cfg   = load_config()
            parts = key.split(".")
            node  = cfg
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            # api_id must be stored as int
            node[parts[-1]] = int(value) if parts[-1] == "api_id" else value
            save_config(cfg)
            app.config["JOB_ALERT_CONFIG"] = cfg
        return redirect(url_for("configure") + "#secrets")

    # ── Configure — Scheduler ──────────────────────────────────────────────────

    @app.route("/configure/scheduler", methods=["POST"])
    def configure_scheduler():
        try:
            minutes = max(5, int(request.form.get("interval_minutes", 60)))
        except ValueError:
            minutes = 60
        cfg = load_config()
        cfg.setdefault("scheduler", {})["interval_minutes"] = minutes
        save_config(cfg)
        app.config["JOB_ALERT_CONFIG"] = cfg
        return redirect(url_for("configure") + "#scheduler")

    # ── Configure — Sources ────────────────────────────────────────────────────

    @app.route("/configure/source/add", methods=["POST"])
    def configure_source_add():
        f         = request.form
        src_type  = f.get("type", "")
        name      = f.get("name", "").strip()
        url       = f.get("url", "").strip()
        if not (src_type and name and url):
            return redirect(url_for("configure") + "#sources")

        source: dict = {"name": name, "type": src_type, "url": url}

        if src_type in ("api_json", "rss"):
            fields = {}
            for field in ("title", "company", "location", "url", "skills"):
                val = f.get(f"field_{field}", "").strip()
                if val:
                    fields[field] = val
            if fields:
                source["fields"] = fields

        elif src_type == "html_scrape":
            selectors = {}
            for sel in ("job_container", "title", "company", "location", "url", "skills"):
                val = f.get(f"sel_{sel}", "").strip()
                if val:
                    selectors[sel] = val
            if selectors:
                source["selectors"] = selectors

        cfg = load_config()
        sources = cfg.setdefault("sources", [])
        # Replace if name already exists, otherwise append
        idx = next((i for i, s in enumerate(sources) if s.get("name") == name), None)
        if idx is not None:
            sources[idx] = source
        else:
            sources.append(source)
        save_config(cfg)
        app.config["JOB_ALERT_CONFIG"] = cfg
        return redirect(url_for("configure") + "#sources")

    @app.route("/configure/source/remove", methods=["POST"])
    def configure_source_remove():
        name = request.form.get("name", "")
        if name:
            cfg = load_config()
            cfg["sources"] = [s for s in cfg.get("sources", []) if s.get("name") != name]
            save_config(cfg)
            app.config["JOB_ALERT_CONFIG"] = cfg
        return redirect(url_for("configure") + "#sources")

    # ── Configure — Preferences (chip form POST) ───────────────────────────────

    @app.route("/configure/preferences", methods=["POST"])
    def configure_preferences():
        f = request.form

        def with_custom(checked_vals: list, custom_field: str) -> list:
            extras = [v.strip() for v in f.get(custom_field, "").split(",") if v.strip()]
            seen, result = set(), []
            for v in checked_vals + extras:
                if v.lower() not in seen:
                    seen.add(v.lower())
                    result.append(v)
            return result

        prefs = {
            "seniority": {
                "include": with_custom(f.getlist("seniority_include"), "custom_seniority"),
                "exclude": with_custom(f.getlist("seniority_exclude"), "custom_seniority_exclude"),
            },
            "field_keywords": with_custom(f.getlist("field_keywords"), "custom_field"),
            "locations":      with_custom(f.getlist("locations"),      "custom_locations"),
            "dashboard": {
                "role_filters":  with_custom(f.getlist("role_filters"),  "custom_role_filters"),
                "skill_filters": with_custom(f.getlist("skill_filters"), "custom_skill_filters"),
            },
        }
        save_preferences(prefs)
        return redirect(url_for("configure") + "#preferences")

    return app


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mask(value) -> dict:
    """Return a display-safe dict for a secret value."""
    if is_placeholder(value):
        return {"set": False, "display": "Not configured"}
    return {"set": True, "display": "••••••••••••"}
