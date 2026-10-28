import logging

from langchain_core.output_parsers import JsonOutputParser

from src.ai.inputs import common_inputs
from src.ai.prompts.music_prompt import music_suggestion_prompt
from src.ai.quality import label_music
from src.Schemas.music import MusicSuggestionOutput
from src.services.openai_service import openai_service
from src.config.log_safety import safe_error

logger = logging.getLogger(__name__)


def get_state_val(state, key, default=""):
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def update_state(state, updates):
    if isinstance(state, dict):
        state.update(updates)
        return state
    else:
        return updates


def music_node(state):
    try:
        llm = openai_service.get_llm("music", temperature=0.7)
        parser = JsonOutputParser(pydantic_object=MusicSuggestionOutput)
        chain = music_suggestion_prompt | llm | parser

        # Extract script / visual context
        script = get_state_val(state, "script", "")
        scenes = get_state_val(state, "scenes", [])
        if script:
            script_summary = script[:400]
        elif scenes:
            script_summary = " ".join([f"Scene {s.get('scene_number', i+1)}: {s.get('what_to_show', '')}" for i, s in enumerate(scenes[:3])])
        else:
            script_summary = get_state_val(state, "idea", "")

        response = chain.invoke({
            **common_inputs(state),
            "script_summary": script_summary,
            "format_instructions": parser.get_format_instructions()
        })
        
        # Suggestions come from the model's memory, not a music catalogue.
        songs = label_music(response.get("songs", []))
        updates = {
            "scene_music": songs,
            "trending_instagram_audio": response.get("trending_instagram_audio", []),
            "trending_tiktok_audio": response.get("trending_tiktok_audio", []),
            "trending_youtube_shorts_audio": response.get("trending_youtube_shorts_audio", [])
        }
    except Exception as e:
        logger.error("Music node error: %s", safe_error(e))
        updates = {
            "scene_music": [],
            "trending_instagram_audio": [],
            "trending_tiktok_audio": [],
            "trending_youtube_shorts_audio": []
        }
    return update_state(state, updates)
