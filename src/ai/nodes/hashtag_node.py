import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential
)

from src.ai.prompts.hashtag_prompt import hashtag_prompt
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
def generate_hashtags(payload):
    llm = openai_service.get_llm()
    parser = JsonOutputParser()
    chain = hashtag_prompt | llm | parser
    return chain.invoke(payload)


def hashtag_node(state):
    updates = {}
    try:
        hashtags = generate_hashtags(
            {
                "script": get_state_val(state, "script"),
                "audience": get_state_val(state, "audience")
            }
        )

        cleaned = []
        seen = set()

        for tag in hashtags:
            hashtag = tag["hashtag"].lower()
            if hashtag not in seen:
                cleaned.append(tag)
                seen.add(hashtag)

        updates["hashtags"] = cleaned
        logger.info(
            f"Generated {len(cleaned)} hashtags"
        )

    except Exception as e:
        logger.error(
            f"Hashtag generation failed {e}"
        )
        updates["hashtags"] = []
        updates["hashtag_error"] = str(e)

    return update_state(state, updates)