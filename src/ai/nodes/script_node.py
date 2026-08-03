import logging

from src.services.openai_service import openai_service
from src.ai.prompts.script_prompt import script_prompt

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


def format_scenes(scenes):
    formatted = []
    for scene in scenes:
        formatted.append(
            f"""
Scene {scene.get('scene_number', '')}

Title:
{scene.get('title', '')}

Duration:
{scene.get('duration', '')}

Camera:
{scene.get('camera_angle', '')}

Movement:
{scene.get('camera_movement', '')}

Lighting:
{scene.get('lighting', '')}

Broll:
{scene.get('broll', '')}

Voiceover:
{scene.get('script_segment', '')}
"""
        )
    return "\n".join(formatted)


def script_node(state):
    logger.info("Stage: Script Generated - Processing Started")
    updates = {}
    try:
        llm = openai_service.get_llm()
        chain = script_prompt | llm

        scenes = get_state_val(state, "scenes", [])
        formatted_scenes = format_scenes(scenes)

        response = chain.invoke(
            {
                "hook": get_state_val(state, "hook"),
                "scenes": formatted_scenes,
                "audience": get_state_val(state, "audience"),
                "platform": get_state_val(state, "platform")
            }
        )

        script = response.content.strip()

        if len(script) < 100:
            raise ValueError(
                "Generated script too short"
            )

        updates["script"] = script
        logger.info(
            "Stage: Script Generated - Success. Script generated successfully"
        )

    except Exception as e:
        logger.error(
            f"Stage: Script Generated - Failed: {e}"
        )
        updates["script"] = ""
        updates["script_error"] = str(e)

    return update_state(state, updates)