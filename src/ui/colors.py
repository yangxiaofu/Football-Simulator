"""Optional ANSI color formatting for terminal displays (Phase 4 Prompt #9)."""

from src.utils.constants import (
    ANSI_RESET, ANSI_BOLD, ANSI_DIM, ANSI_CYAN, ANSI_YELLOW, ANSI_GREEN, ANSI_RED,
)


def color(text: str, code: str, use_color: bool) -> str:
    """Wrap text in ANSI color if use_color=True, else return plain."""
    if not use_color:
        return text
    return f"{code}{text}{ANSI_RESET}"


def bold(text, use_color=True):
    return color(text, ANSI_BOLD, use_color)


def dim(text, use_color=True):
    return color(text, ANSI_DIM, use_color)


def cyan(text, use_color=True):
    return color(text, ANSI_CYAN, use_color)


def yellow(text, use_color=True):
    return color(text, ANSI_YELLOW, use_color)


def green(text, use_color=True):
    return color(text, ANSI_GREEN, use_color)


def red(text, use_color=True):
    return color(text, ANSI_RED, use_color)
