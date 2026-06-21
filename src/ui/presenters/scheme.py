"""Scheme Settings presenter (T-10, Milestone 5.12)."""
from __future__ import annotations

from src.utils.constants import SCHEME_ATTRIBUTE_MAP_DEFENSE, SCHEME_ATTRIBUTE_MAP_OFFENSE


def _label(key: str) -> str:
    """Convert a scheme key to a display label.

    Keys starting with a digit use hyphens ('4_3' → '4-3').
    Word keys are title-cased with spaces ('west_coast' → 'West Coast').
    """
    if key and key[0].isdigit():
        return key.replace("_", "-")
    return key.replace("_", " ").title()


def build_scheme_settings(conn) -> dict:
    """Return current scheme values and all valid options for the user's team."""
    state = conn.execute("SELECT user_team_id FROM league WHERE id = 1").fetchone()
    team_id = state["user_team_id"]
    row = conn.execute(
        "SELECT scheme_offense, scheme_defense FROM team WHERE id = ?", (team_id,)
    ).fetchone()
    return {
        "ok": True,
        "current_offense": row["scheme_offense"],
        "current_defense": row["scheme_defense"],
        "offense_options": [
            {"value": k, "label": _label(k)} for k in SCHEME_ATTRIBUTE_MAP_OFFENSE
        ],
        "defense_options": [
            {"value": k, "label": _label(k)} for k in SCHEME_ATTRIBUTE_MAP_DEFENSE
        ],
    }


def apply_scheme_update(conn, offense: str, defense: str) -> dict:
    """Validate and persist scheme changes for the user's team."""
    if offense not in SCHEME_ATTRIBUTE_MAP_OFFENSE:
        raise ValueError(f"Invalid offense scheme: {offense!r}")
    if defense not in SCHEME_ATTRIBUTE_MAP_DEFENSE:
        raise ValueError(f"Invalid defense scheme: {defense!r}")
    state = conn.execute("SELECT user_team_id FROM league WHERE id = 1").fetchone()
    team_id = state["user_team_id"]
    with conn:
        conn.execute(
            "UPDATE team SET scheme_offense = ?, scheme_defense = ? WHERE id = ?",
            (offense, defense, team_id),
        )
    return {"ok": True}
