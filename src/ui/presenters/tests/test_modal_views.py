"""Phase 6 P7b — shape tests for the modal view-models.

PitchMeetingView / OfferBuilderView / NegotiationResultView built via the
free_agency presenter against the in-memory fixture from test_free_agency.
(Cut/Restructure sub-views are shape-asserted in test_player.py.)
"""
from src.ui.presenters import free_agency
from src.ui.presenters.tests.test_free_agency import _make_db

PITCH_KEYS = {"player_id", "player_name", "position", "overall",
              "asking_salary", "interest_label", "interest_signal",
              "market", "can_offer", "note"}
OFFER_KEYS = {"player_id", "player_name", "position", "market",
              "cap_available", "defaults", "bounds"}
RESULT_KEYS = {"ok", "accepted", "outcome", "player_name",
               "cap_impact", "message"}
MARKET_KEYS = {"low", "fair", "premium"}


def test_pitch_meeting_view_shape():
    conn = _make_db(with_fa_players=1)
    v = free_agency.build_pitch_meeting(conn, 1)
    assert set(v.keys()) == PITCH_KEYS
    assert set(v["market"].keys()) == MARKET_KEYS
    assert isinstance(v["can_offer"], bool)
    assert v["can_offer"] is True              # player 1 is a free agent


def test_offer_builder_view_shape():
    conn = _make_db(with_fa_players=1)
    v = free_agency.build_offer_builder(conn, 1)
    assert set(v.keys()) == OFFER_KEYS
    assert set(v["market"].keys()) == MARKET_KEYS
    assert set(v["defaults"].keys()) == {
        "years", "aav", "signing_bonus", "guaranteed_money"}
    assert set(v["bounds"].keys()) == {
        "min_years", "max_years",
        "max_signing_bonus_pct", "max_guaranteed_pct"}
    assert v["defaults"]["years"] >= v["bounds"]["min_years"]
    assert v["defaults"]["aav"] > 0


def test_negotiation_result_view_accepted():
    v = free_agency.build_negotiation_result({
        "ok": True, "accepted": True, "player_name": "Test Back",
        "cap_impact": "$5.0M", "message": "signed",
    })
    assert set(v.keys()) == RESULT_KEYS
    assert v["accepted"] is True
    assert v["outcome"] == "accepted"


def test_negotiation_result_view_rejected():
    v = free_agency.build_negotiation_result({
        "ok": True, "accepted": False, "player_name": "Test Back",
        "cap_impact": "$0", "message": "Rejected: walked",
    })
    assert v["accepted"] is False
    assert v["outcome"] == "rejected"


def test_offer_builder_player_not_found():
    conn = _make_db(with_fa_players=0)
    v = free_agency.build_offer_builder(conn, 12345)
    assert v.get("ok") is False
