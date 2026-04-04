"""
Loads and saves the two config files:

  config.yaml                      — secrets + sources (Telegram tokens, scrapers)
  configuration/preferences.yaml   — user preferences (seniority, locations, filters)
"""
import os
import yaml

_BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
_CONFIG      = os.path.join(_BASE_DIR, "config.yaml")
_CFG_EXAMPLE = os.path.join(_BASE_DIR, "config.example.yaml")
_PREFS       = os.path.join(_BASE_DIR, "configuration", "preferences.yaml")


def load_config() -> dict:
    """Load config.yaml (Telegram credentials, sources, scheduler)."""
    path = _CONFIG if os.path.exists(_CONFIG) else _CFG_EXAMPLE
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(cfg: dict) -> None:
    """Write config.yaml. Creates the file if it doesn't exist yet."""
    with open(_CONFIG, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def is_placeholder(value) -> bool:
    """Return True if a config value is still the example placeholder."""
    return not value or "YOUR_" in str(value)


def load_preferences() -> dict:
    """Load configuration/preferences.yaml (user search preferences)."""
    with open(_PREFS, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_preferences(prefs: dict) -> None:
    """Write configuration/preferences.yaml."""
    header = (
        "# Your job search preferences.\n"
        "# Edit this file directly OR use the configure page at http://localhost:5001/configure\n\n"
    )
    with open(_PREFS, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.dump(prefs, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
