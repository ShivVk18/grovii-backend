import logging
from src.ai.prompts.music_prompt import music_suggestion_prompt
from src.services.openai_service import openai_service
from langchain_core.output_parsers import JsonOutputParser
from src.Schemas.music import MusicSuggestionOutput

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
        llm = openai_service.get_llm()
        parser = JsonOutputParser(pydantic_object=MusicSuggestionOutput)
        chain = music_suggestion_prompt | llm | parser

        response = chain.invoke({
            "idea": get_state_val(state, "idea"),
            "tone": get_state_val(state, "tone"),
            "audience": get_state_val(state, "audience"),
            "language": get_state_val(state, "language", "English"),
            "platform": get_state_val(state, "platform"),
            "format_instructions": parser.get_format_instructions()
        })
        
        songs = response.get("songs", [])
        updates = {
            "scene_music": songs,
            "trending_instagram_audio": response.get("trending_instagram_audio", []),
            "trending_tiktok_audio": response.get("trending_tiktok_audio", []),
            "trending_youtube_shorts_audio": response.get("trending_youtube_shorts_audio", [])
        }
    except Exception as e:
        logger.error(f"Music node error: {e}")
        updates = {
            "scene_music": [],
            "trending_instagram_audio": [],
            "trending_tiktok_audio": [],
            "trending_youtube_shorts_audio": []
        }
    return update_state(state, updates)
