"""Phase D: AI output quality rules enforced in code (QUAL-01..04, hashtags, music)."""
import itertools
import json
from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from src.Schemas.storyboard_schema import CreateStoryboardRequest
from tests.conftest import VALID_STORYBOARD


# ------------------------------------------------------------- timeline ----
def test_scene_count_scales_with_duration():
    from src.ai.timeline import scene_count_for

    assert [scene_count_for(d) for d in (15, 30, 45, 60, 90, 180)] == [3, 5, 8, 8, 8, 8]  # ~one scene per 6s, 3..8


def test_timeline_problems_are_reported():
    from src.ai.timeline import timeline_problems

    ok = [{"duration_seconds": 10}, {"duration_seconds": 10}, {"duration_seconds": 10}]
    short = [{"duration_seconds": 4}, {"duration_seconds": 5}]
    assert timeline_problems(ok, 30) == []
    assert any("sum to 9" in p for p in timeline_problems(short, 30))
    assert timeline_problems([{"duration_seconds": 0}, {"duration_seconds": 30}], 30)


def test_rescale_makes_exact_contiguous_timeline():
    from src.ai.timeline import apply_timeline

    scenes = [{"duration_seconds": 3}, {"duration_seconds": 4}, {"duration_seconds": 5}, {"duration_seconds": 4}]
    out = apply_timeline(scenes, 60)
    durations = [s["duration_seconds"] for s in out]
    assert sum(durations) == 60 and min(durations) >= 1
    assert out[0]["start_seconds"] == 0 and out[-1]["end_seconds"] == 60
    for a, b in zip(out, out[1:]):
        assert a["end_seconds"] == b["start_seconds"]
    assert [s["scene_number"] for s in out] == [1, 2, 3, 4]
    assert all(s["duration"] == str(s["duration_seconds"]) for s in out)


# ------------------------------------------------------- scene node (D1/D2) ----
def _fake_replies(*replies):
    from src.services import openai_service as mod

    it = iter(replies)
    return patch.object(mod, "_chat_model", side_effect=lambda **kw: GenericFakeChatModel(
        messages=itertools.repeat(AIMessage(content=next(it))), callbacks=kw.get("callbacks")))


def _scenes_json(durations, example=None):
    return json.dumps({"chosen_example": example, "scenes": [
        {"title": f"S{i}", "duration_seconds": d, "what_to_record": f"Record shot {i}",
         "where": "Kitchen counter", "framing": "Close-up from above",
         "voiceover": f"Spoken line number {i}.", "onscreen_text": f"Step {i}", "tips": "Use window light",
         "emotion": "calm", "advanced": {"camera_angle": "top-down"}}
        for i, d in enumerate(durations, 1)]})


def _state(**over):
    req = CreateStoryboardRequest(**{**VALID_STORYBOARD, **over})
    return {**req.model_dump(), "hook": "Stop making bitter coffee", "scenes": [], "script": ""}


def test_scene_node_retries_with_feedback_when_durations_are_wrong():
    from src.ai.nodes.scene_node import scene_node

    with _fake_replies(_scenes_json([3, 3, 3, 3, 3]), _scenes_json([6, 6, 6, 6, 6])) as factory:
        out = scene_node(_state(duration=30))
    assert factory.call_count == 2
    assert [s["duration_seconds"] for s in out["scenes"]] == [6, 6, 6, 6, 6]
    assert out["timeline_adjusted"] is False


def test_scene_node_rescales_as_last_resort():
    from src.ai.nodes.scene_node import scene_node

    with _fake_replies(_scenes_json([3, 3, 3, 3, 3]), _scenes_json([2, 2, 2, 2, 2])):
        out = scene_node(_state(duration=30))
    assert sum(s["duration_seconds"] for s in out["scenes"]) == 30
    assert out["scenes"][-1]["end_seconds"] == 30
    assert out["timeline_adjusted"] is True


def test_script_is_built_from_scene_voiceovers_and_hook_opens_scene_one():
    from src.ai.nodes.scene_node import scene_node
    from src.ai.nodes.script_node import script_node

    with _fake_replies(_scenes_json([6, 6, 6, 6, 6])):
        state = {**_state(duration=30)}
        state.update(scene_node(state))  # nodes return updates; LangGraph merges them
    state.update(script_node(state))
    voiceovers = [s["voiceover_example"] for s in state["scenes"]]
    assert voiceovers[0].startswith("Stop making bitter coffee")
    assert state["script"] == "\n\n".join(voiceovers)  # one source of truth


def test_open_brief_choice_is_recorded():
    from src.ai.nodes.scene_node import scene_node

    with _fake_replies(_scenes_json([6, 6, 6, 6, 6], example="Mumbai vada pav")):
        out = scene_node(_state(duration=30, idea="Quick street food recipe for my channel"))
    assert out["brief_choice"] == "Mumbai vada pav"


def test_constraints_reach_the_scene_prompt():
    from src.ai.nodes.scene_node import build_scene_inputs

    inputs = build_scene_inputs(_state(faceless=True, location="Small apartment kitchen", equipment="Phone only"))
    assert "faceless" in inputs["constraints"].lower()
    assert "Small apartment kitchen" in inputs["constraints"]
    assert "Phone only" in inputs["constraints"]


# ------------------------------------------------------------ hook (D4) ----
def test_best_hook_is_picked_in_code():
    from src.ai.quality import pick_best_hook

    candidates = [
        {"hook": "This one is far too long to say in the first three seconds of a video ok", "score": 99},
        {"hook": "Your espresso is bitter for one reason", "score": 91},
        {"hook": "Coffee tips", "score": 95},  # too short to be a hook
        {"hook": "Stop wasting good beans", "score": 80},
    ]
    assert pick_best_hook(candidates) == "Your espresso is bitter for one reason"


def test_graph_has_no_hook_regenerator_and_script_needs_no_llm():
    from src.ai.graph import graph

    assert "hook_regenerator" not in graph.nodes
    from src.ai.nodes import script_node as mod
    assert not hasattr(mod, "openai_service")


def test_hook_node_makes_one_llm_call_even_on_failure():
    from src.ai.nodes.hook_node import hook_node

    with _fake_replies("not json at all", "x", "x") as factory:
        out = hook_node(_state())
    assert factory.call_count == 1  # no stacked node-level retries (BACKLOG #22)
    assert out["hook"] == "" and out["hook_error"]


# ------------------------------------------------------- language (D3) ----
def test_every_prompt_receives_language_and_tone():
    import importlib

    from tests.test_prompt_injection import PROMPTS

    for module, name in PROMPTS:
        prompt = getattr(importlib.import_module(module), name)
        assert {"language", "tone"} <= set(prompt.input_variables), name


@pytest.mark.parametrize("language,texts,ok", [
    ("Hinglish", {"script": "Main pehle har din late uthta tha, phir maine yeh habit try kiya"}, True),
    ("Hinglish", {"script": "मैं पहले देर से उठता था"}, False),
    ("Hinglish", {"script": "I used to wake up late every single day until I tried this"}, False),
    ("Spanish", {"script": "Estos son los tres hábitos que uso para tener una mañana productiva"}, True),
    ("Spanish", {"script": "Estos son los tres hábitos", "captions": "Here are the three habits you need for a productive morning routine"}, False),
    ("English", {"script": "Three habits for a productive morning"}, True),
])
def test_language_check(language, texts, ok):
    from src.ai.quality import language_problems

    assert (language_problems(language, texts) == []) is ok


# ------------------------------------------------------ hashtags/music (D7) ----
def test_hashtags_are_cleaned_and_capped():
    from src.ai.quality import clean_hashtags

    raw = ["#coffee", "Coffee", "#fyp", "#viral", "espresso tips", "#EspressoTips", "#barista",
           "#reels", "#a1", "#a2", "#a3", "#a4", "#a5", "#a6", "#a7", "#a8", "#a9"]
    out = clean_hashtags(raw)
    lowered = [t.lower() for t in out]
    assert all(t.startswith("#") and " " not in t for t in out)
    assert "#fyp" not in lowered and "#viral" not in lowered and "#reels" not in lowered
    assert len(lowered) == len(set(lowered))
    assert len(out) == 10
    assert out[:3] == ["#coffee", "#espressotips", "#barista"] or out[0] == "#coffee"


def test_music_is_labelled_as_unverified_style_reference():
    from src.ai.quality import label_music

    out = label_music([{"song_name": "Nightcall", "artist": "Kavinsky", "why_fits": "dark synth"}])
    assert out[0]["verified"] is False
    assert "style reference" in out[0]["label"].lower()
    assert "commercial" in out[0]["licensing_note"].lower()


# --------------------------------------------------- constraints (D5) ----
def test_constraint_fields_are_optional_and_validated():
    from pydantic import ValidationError

    req = CreateStoryboardRequest(**VALID_STORYBOARD)
    assert req.faceless is False and req.location is None and req.equipment is None
    req = CreateStoryboardRequest(**{**VALID_STORYBOARD, "faceless": True, "location": "  Park  ", "equipment": "Phone"})
    assert req.location == "Park"
    with pytest.raises(ValidationError):
        CreateStoryboardRequest(**{**VALID_STORYBOARD, "location": "x" * 121})
