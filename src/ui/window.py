"""pywebview window entry point for Football Simulator GUI.

This module and src/ui/api.py are the only Python files in src/ui/ that
import webview. Everything else is plain Python or static assets.

Usage:
    python -m src.ui.window saves/my_franchise.db
    python -m src.ui.window saves/my_franchise.db --debug
"""
from __future__ import annotations

import argparse
from pathlib import Path

import webview

from src.ui.api import Api
from src.utils.constants import (
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)


def main(save_path: str | None = None, debug: bool = False) -> None:
    api = Api(save_path)
    index = Path(__file__).parent / "static" / "index.html"
    webview.create_window(
        WINDOW_TITLE,
        url=str(index),
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT),
    )
    webview.start(debug=debug, http_server=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Football Simulator GUI")
    parser.add_argument("save_path", nargs="?", default=None, help="Path to franchise .db file (omit to show Title Screen)")
    parser.add_argument("--debug", action="store_true", help="Open DevTools on launch")
    args = parser.parse_args()
    main(args.save_path, args.debug)
