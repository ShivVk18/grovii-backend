from src.ai.prompts.music_prompt import music_suggestion_prompt
from src.services.openai_service import openai_service
from langchain_core.output_parsers import JsonOutputParser
from src.Schemas.music import MusicSuggestionOutput


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
    llm = openai_service.get_llm()
    parser = JsonOutputParser(pydantic_object=MusicSuggestionOutput)
    chain = music_suggestion_prompt | llm | parser

    response = chain.invoke({
        "tone": get_state_val(state, "tone"),
        "platform": get_state_val(state, "platform"),
        "scenes": get_state_val(state, "scenes", []),
        "format_instructions": parser.get_format_instructions()
    })
    
    updates = {
        "scene_music": response.get("scene_music", [])
    }
    return update_state(state, updates)

