import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential
)

from src.ai.prompts.caption_prompts import caption_prompt
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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(
        multiplier=1,
        min=1,
        max=5
    )
)
def generate_captions(payload):
    llm = openai_service.get_llm("caption")
    parser = JsonOutputParser()
    chain = caption_prompt | llm | parser
    return chain.invoke(payload)


def caption_node(state):
    updates = {}
    try:
        captions = generate_captions(
            {
                "script": get_state_val(state, "script"),
                "tone": get_state_val(state, "tone"),
                "audience": get_state_val(state, "audience")
            }
        )

        cleaned = []
        seen = set()

        for caption in captions:
            text = caption["caption"].strip()
            if text.lower() not in seen:
                cleaned.append(
                    {
                        "caption": text
                    }
                )
                seen.add(
                    text.lower()
                )

        if len(cleaned) < 3:
            logger.warning(
                "Less than 3 captions generated"
            )

        updates["captions"] = cleaned
        logger.info(
            f"Generated {len(cleaned)} captions"
        )

    except Exception as e:
        logger.error(
            f"Caption generation failed: {e}"
        )
        updates["captions"] = []
        updates["caption_error"] = str(e)

    return update_state(state, updates)

