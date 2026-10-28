import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential
)

from src.ai.prompts.hook_prompts import hook_prompt
from src.services.openai_service import openai_service


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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(
        multiplier=1,
        min=1,
        max=5
    )
)
def generate_hook(payload):
    llm = openai_service.get_llm("hook")
    chain = hook_prompt | llm
    return chain.invoke(payload)


def hook_node(state):
    logger.info("Stage: Hook Generated - Processing Started")
    updates = {}
    try:
        response = generate_hook(
            {
                "idea": get_state_val(state, "idea"),
                "goal": get_state_val(state, "goal"),
                "tone": get_state_val(state, "tone"),
                "audience": get_state_val(state, "audience"),
                "platform": get_state_val(state, "platform")
            }
        )

        hook = response.text.strip()  # .text: Gemini returns content as a list of parts

        if len(hook.split()) > 15:
            raise ValueError(
                "Hook exceeds maximum word limit"
            )

        if len(hook) < 10:
            raise ValueError(
                "Hook too short"
            )

        updates["hook"] = hook
        logger.info(
            f"Stage: Hook Generated - Success. Generated hook: {hook}"
        )

    except Exception as e:
        logger.error(
            f"Stage: Hook Generated - Failed: {e}"
        )
        updates["hook"] = ""
        updates["hook_error"] = str(e)

    return update_state(state, updates)