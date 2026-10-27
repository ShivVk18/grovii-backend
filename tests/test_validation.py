"""VAL-01: storyboard input validation, boundaries and field-level error format."""
import pytest
from pydantic import ValidationError

from src.models.storyboard import Storyboard
from src.Schemas.storyboard_schema import (
    CreateStoryboardRequest,
    UpdateStoryboardRequest,
)
from tests.conftest import VALID_STORYBOARD


def make(**overrides):
    return CreateStoryboardRequest(**{**VALID_STORYBOARD, **overrides})


def error_fields(exc: ValidationError) -> set[str]:
    return {str(e["loc"][0]) for e in exc.errors()}


# ----------------------------------------------------------- boundaries ----
@pytest.mark.parametrize("field,value,ok", [
    ("idea", "x" * 9, False),
    ("idea", "x" * 10, True),
    ("idea", "x" * 1000, True),
    ("idea", "x" * 1001, False),
    ("idea", "   \n\t  ", False),
    ("idea", "   short   ", False),          # 5 chars after trimming
    ("duration", 14, False),
    ("duration", 15, True),
    ("duration", 180, True),
    ("duration", 181, False),
    ("duration", -5, False),
    ("duration", 30.5, False),
    ("duration", "abc", False),
    ("audience", "", False),
    ("audience", "x", False),
    ("audience", "xy", True),
    ("audience", "x" * 200, True),
    ("audience", "x" * 201, False),
])
def test_boundaries(field, value, ok):
    if ok:
        make(**{field: value})
    else:
        with pytest.raises(ValidationError) as exc:
            make(**{field: value})
        assert field in error_fields(exc.value)


def test_whitespace_is_trimmed():
    req = make(idea="   A 30 second espresso routine   ", audience="  Coffee lovers ")
    assert req.idea == "A 30 second espresso routine"
    assert req.audience == "Coffee lovers"


# --------------------------------------------------------- allowed values ----
@pytest.mark.parametrize("field,value", [
    ("platform", "myspace"), ("platform", ""), ("tone", "sarcastic villain"),
    ("tone", "   "), ("goal", "world domination"), ("language", "Klingon"),
    ("style", "anything goes"),
])
def test_unknown_values_rejected(field, value):
    with pytest.raises(ValidationError) as exc:
        make(**{field: value})
    assert field in error_fields(exc.value)


@pytest.mark.parametrize("field,given,stored", [
    # values the frontend sends today are stored unchanged
    ("platform", "reels", "reels"), ("platform", "tiktok", "tiktok"), ("platform", "shorts", "shorts"),
    ("tone", "energetic", "energetic"), ("goal", "educate", "educate"),
    ("style", "talking_head", "talking_head"), ("language", "Hindi", "Hindi"),
    # labels used by the eval dataset map to the same keys, case-insensitively
    ("platform", "Instagram Reels", "reels"), ("platform", "YouTube Shorts", "shorts"),
    ("platform", "TikTok", "tiktok"), ("platform", "LinkedIn", "linkedin"),
    ("tone", "Professional", "professional"), ("goal", "Promote", "promote"),
    ("style", "Talking Head", "talking_head"), ("language", "hinglish", "Hinglish"),
    ("language", "SPANISH", "Spanish"),
])
def test_allowed_values_and_aliases(field, given, stored):
    assert getattr(make(**{field: given}), field) == stored


def test_language_defaults_to_english():
    data = {k: v for k, v in VALID_STORYBOARD.items() if k != "language"}
    assert CreateStoryboardRequest(**data).language == "English"


def test_update_request_validates_only_given_fields():
    assert UpdateStoryboardRequest(title="New title").model_dump(exclude_unset=True) == {"title": "New title"}
    with pytest.raises(ValidationError):
        UpdateStoryboardRequest(idea="")
    with pytest.raises(ValidationError):
        UpdateStoryboardRequest(duration=0)
    with pytest.raises(ValidationError):
        UpdateStoryboardRequest(title="x" * 201)


# ------------------------------------------------- API error format (422) ----
def test_generate_rejects_bad_input_with_field_errors_and_creates_nothing(client, auth_headers, db):
    payload = {**VALID_STORYBOARD, "idea": "  ", "duration": 999, "platform": "myspace"}
    r = client.post("/storyboards/generate", json=payload, headers=auth_headers)

    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error"
    assert isinstance(body["detail"], str) and body["detail"]  # frontend renders detail directly
    assert set(body["errors"]) == {"idea", "duration", "platform"}
    assert body["errors"]["idea"] == "Idea must be at least 10 characters."
    assert body["errors"]["duration"] == "Duration must be between 15 and 180 seconds."
    assert "reels" in body["errors"]["platform"]
    assert db.query(Storyboard).count() == 0


def test_patch_rejects_bad_input(client, auth_headers):
    r = client.post("/storyboards", json=VALID_STORYBOARD, headers=auth_headers)
    assert r.status_code == 201
    r = client.patch(f"/storyboards/{r.json()['id']}", json={"idea": ""}, headers=auth_headers)
    assert r.status_code == 422
    assert "idea" in r.json()["errors"]


def test_malformed_json_gets_readable_error(client, auth_headers):
    r = client.post("/storyboards/generate", content="{not json", headers={**auth_headers, "Content-Type": "application/json"})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)
