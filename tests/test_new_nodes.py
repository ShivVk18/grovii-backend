import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from src.ai.state import GraphState
from src.ai.nodes.trend_node import trend_node
from src.ai.nodes.music_node import music_node
from src.ai.nodes.repurpose_node import repurpose_node
from src.ai.graph import graph

@pytest.fixture
def base_state():
    return {
        "idea": "Test idea",
        "goal": "Test goal",
        "tone": "Educational",
        "style": "Fast-paced",
        "audience": "Developers",
        "duration": 60,
        "platform": "YouTube",
        "hook": "Test hook",
        "scenes": [],
        "script": "Test script",
        "captions": [],
        "hashtags": [],
        "regenerated_hooks": [],
        "trends": {},
        "scene_music": [],
        "repurposed_content": {}
    }

@patch('langchain_google_genai.ChatGoogleGenerativeAI.invoke')
def test_trend_node(mock_invoke, base_state):
    mock_invoke.return_value = AIMessage(content='{"hooks": ["Trend hook"], "sounds": ["Trend sound"], "transitions": ["Trend transition"], "best_duration": "15s", "posting_time": "10 AM", "editing_style": "Fast", "content_gaps": []}')
    
    new_state = trend_node(base_state)
    assert new_state["trends"]["posting_time"] == "10 AM"

@patch('langchain_google_genai.ChatGoogleGenerativeAI.invoke')
def test_music_node(mock_invoke, base_state):
    # Current music schema (song_name/artist/why_fits...); the old mock used a
    # pre-August shape and failed since before Phase A (BACKLOG #1).
    mock_invoke.return_value = AIMessage(content='{"songs": [{"song_name": "Sunflower", "artist": "Post Malone", '
                                                 '"why_fits": "Warm, mid-tempo", "best_scene": "Scene 1-2", "mood": "Chill pop"}]}')

    new_state = music_node(base_state)
    assert len(new_state["scene_music"]) == 1
    song = new_state["scene_music"][0]
    assert song["song_name"] == "Sunflower"
    assert song["verified"] is False and "licensing_note" in song

@patch('langchain_google_genai.ChatGoogleGenerativeAI.invoke')
def test_repurpose_node(mock_invoke, base_state):
    mock_invoke.return_value = AIMessage(content='{"linkedin": "LinkedIn Post", "twitter_thread": "Twitter Thread", "carousel": "Carousel Text", "blog": "Blog Post", "newsletter": "Newsletter"}')
    
    new_state = repurpose_node(base_state)
    assert new_state["repurposed_content"]["linkedin"] == "LinkedIn Post"

def test_graph_compilation():
    # Verify graph can be compiled
    assert graph is not None
