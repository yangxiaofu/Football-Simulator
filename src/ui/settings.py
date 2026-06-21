"""User settings persistence for Football Simulator.

Stores settings in a platform-appropriate location using stdlib only (no platformdirs).
All public functions are module-level — no class needed.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "FootballSimulator"
DEFAULTS: dict = {
    "autosave": True,
    "sim_speed": "normal",   # 'fast' | 'normal' | 'instant'
    "autopilot": False,      # skip press-conference prompts when advancing weeks
    "recent_saves": [],      # list of recently opened .db paths (most recent first)
}
_MAX_RECENT = 10


def _settings_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME / "settings.json"


def _saves_dir() -> Path:
    """Return the saves directory for the current run mode (dev vs PyInstaller)."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundle — saves live next to the executable
        return Path(sys.executable).parent / "saves"
    # Development — project root / saves
    # This file is at src/ui/settings.py, so .parents[2] = project root
    return Path(__file__).parents[2] / "saves"


def load() -> dict:
    """Load settings from disk. Returns DEFAULTS (merged) if file is missing or corrupt."""
    try:
        path = _settings_path()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                file_data = json.load(f)
            return {**DEFAULTS, **file_data}
    except Exception:
        pass
    return dict(DEFAULTS)


def save(settings: dict) -> None:
    """Atomically write settings to disk. Creates parent directories if needed."""
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    tmp.replace(path)


def add_recent_save(path: str) -> None:
    """Prepend path to recent_saves, deduplicate, cap at _MAX_RECENT, and persist."""
    normalized = str(Path(path).resolve())
    settings = load()
    recent: list = settings.get("recent_saves", [])
    recent = [p for p in recent if p != normalized]
    recent.insert(0, normalized)
    settings["recent_saves"] = recent[:_MAX_RECENT]
    save(settings)
