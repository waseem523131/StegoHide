"""Application configuration utilities."""

import json
from pathlib import Path

DEFAULT_CONFIG = {
    "log_level": "INFO",
    "reports_dir": "reports",
    "output_dir": "output",
    "version": "1.0.0",
}


def get_project_root():
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent


def get_default_config_path():
    """Return the default location for the project config file."""
    return get_project_root() / "config" / "stegohide_config.json"


def load_config(path=None):
    """Load configuration from a JSON file, falling back to defaults."""
    config_path = Path(path) if path else get_default_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            merged = DEFAULT_CONFIG.copy()
            merged.update(loaded)
            return merged
        except json.JSONDecodeError:
            raise ValueError(f"Invalid configuration file: {config_path}")
    return DEFAULT_CONFIG.copy()


def save_default_config(path=None):
    """Create the default configuration file if it does not exist."""
    config_path = Path(path) if path else get_default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(DEFAULT_CONFIG, handle, indent=2)
            handle.write("\n")
    return config_path
