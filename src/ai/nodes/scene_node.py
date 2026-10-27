import logging

from src.ai.prompts.scene_prompt import scene_prompt
from src.Schemas.scene import Scene, SceneList
from src.services.openai_service import openai_service
from langchain_core.output_parsers import JsonOutputParser

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


def scene_node(state):
    logger.info("Stage: Scenes Generated - Processing Started")
    updates = {}
    try:
        llm = openai_service.get_llm("director")
        parser = JsonOutputParser()
        chain = scene_prompt | llm | parser

        scenes = chain.invoke(
            {
                "idea": get_state_val(state, "idea"),
                "hook": get_state_val(state, "hook"),
                "tone": get_state_val(state, "tone"),
                "audience": get_state_val(state, "audience"),
                "language": get_state_val(state, "language", "English")
            }
        )

        if not isinstance(scenes, list) or len(scenes) != 5:
            raise Exception(
                "Expected exactly 5 scenes"
            )

        updates['scenes'] = [
            Scene(**scene).model_dump()
            for scene in scenes
        ]


        logger.info(
            f"Stage: Scenes Generated - Success. Generated {len(updates['scenes'])} scenes"
        )

    except Exception as e:
        logger.error(
            f"Stage: Scenes Generated - Failed: {e}"
        )
        updates['scenes'] = []
        updates['scene_error'] = str(e)

    return update_state(state, updates)