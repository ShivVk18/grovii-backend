import logging

from langchain_core.output_parsers import JsonOutputParser

from src.ai.inputs import common_inputs
from src.ai.prompts.hashtag_prompt import hashtag_prompt
from src.ai.quality import clean_hashtags
from src.config.log_safety import safe_error
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


# No node-level retries: the LLM client and the job queue already retry.
def generate_hashtags(payload):
    llm = openai_service.get_llm("hashtag")
    parser = JsonOutputParser()
    chain = hashtag_prompt | llm | parser
    return chain.invoke(payload)


def hashtag_node(state):
    updates = {}
    try:
        hashtags = generate_hashtags(common_inputs(state))
        if isinstance(hashtags, dict):
            hashtags = hashtags.get("hashtags") or []
        # Code, not the prompt, guarantees: no filler (#fyp, #viral...), no
        # duplicates, '#lowercase' form, at most 10 tags.
        cleaned = [{"hashtag": t} for t in clean_hashtags(hashtags)]

        updates["hashtags"] = cleaned
        logger.info(
            f"Generated {len(cleaned)} hashtags"
        )

    except Exception as e:
        logger.error(
            "Hashtag generation failed: %s", safe_error(e)
        )
        updates["hashtags"] = []
        updates["hashtag_error"] = safe_error(e)

    return update_state(state, updates)