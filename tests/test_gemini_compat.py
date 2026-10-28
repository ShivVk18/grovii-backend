"""Gemini 3.x compatibility: list-shaped message content and thinking tokens."""
import itertools
from unittest.mock import patch

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from src.config import limits

LONG_SCRIPT = "This is the voiceover script line. " * 10


def _list_content(text):
    # Gemini 3.x returns content as a list of parts, not a plain string.
    return AIMessage(content=[{"type": "text", "text": text}])


def _fake(reply):
    from src.services import openai_service as mod

    return patch.object(mod, "_chat_model", side_effect=lambda **kw: GenericFakeChatModel(
        messages=itertools.repeat(reply), callbacks=kw.get("callbacks")))


def test_get_llm_disables_hidden_thinking_by_default():
    from src.services.openai_service import openai_service

    llm = openai_service.get_llm("hook")
    assert llm.thinking_budget == limits.LLM_THINKING_BUDGET == 0
    assert llm.model.endswith("gemini-3.6-flash")


def test_hook_node_reads_list_content():
    from src.ai.nodes.hook_node import hook_node

    with _fake(_list_content("Stop making bitter coffee today")):
        out = hook_node({"idea": "coffee", "goal": "educate", "tone": "calm", "audience": "ab", "platform": "reels"})
    assert out["hook"] == "Stop making bitter coffee today"


def test_script_node_reads_list_content():
    from src.ai.nodes.script_node import script_node

    with _fake(_list_content(LONG_SCRIPT)):
        out = script_node({"hook": "h", "scenes": [], "audience": "ab", "platform": "reels"})
    assert out["script"] == LONG_SCRIPT.strip()
