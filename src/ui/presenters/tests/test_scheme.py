"""Tests for scheme settings presenter (T-10, Milestone 5.12)."""
import pytest
from src.db.connection import get_connection
from src.ui.presenters import scheme


def test_build_scheme_settings_shape(seeded_db):
    conn = get_connection(seeded_db)
    result = scheme.build_scheme_settings(conn)
    assert result["ok"] is True
    assert "current_offense" in result
    assert "current_defense" in result
    assert len(result["offense_options"]) == 8
    assert len(result["defense_options"]) == 8


def test_scheme_option_labels(seeded_db):
    conn = get_connection(seeded_db)
    result = scheme.build_scheme_settings(conn)
    d_labels = {o["value"]: o["label"] for o in result["defense_options"]}
    assert d_labels["4_3"] == "4-3"
    assert d_labels["cover_2"] == "Cover 2"
    o_labels = {o["value"]: o["label"] for o in result["offense_options"]}
    assert o_labels["west_coast"] == "West Coast"


def test_apply_scheme_update_roundtrip(seeded_db):
    conn = get_connection(seeded_db)
    result = scheme.apply_scheme_update(conn, "air_raid", "blitz")
    assert result["ok"] is True
    refreshed = scheme.build_scheme_settings(conn)
    assert refreshed["current_offense"] == "air_raid"
    assert refreshed["current_defense"] == "blitz"


def test_apply_scheme_update_rejects_invalid(seeded_db):
    conn = get_connection(seeded_db)
    with pytest.raises(ValueError):
        scheme.apply_scheme_update(conn, "not_a_real_scheme", "4_3")
