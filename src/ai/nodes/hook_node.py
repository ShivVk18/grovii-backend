import logging

from langchain_core.output_parsers import JsonOutputParser

from src.ai.inputs import common_inputs
from src.ai.prompts.hook_prompts import hook_prompt
from src.ai.quality import pick_best_hook
from src.config.log_safety import safe_error
from src.services.openai_service import openai_service

logger = logging.getLogger(__name__)


def hook_node(state):
    """One LLM call returns scored hook candidates; code picks the best.
    No node-level retries: the client and the job queue already retry."""
    try:
        chain = hook_prompt | openai_service.get_llm("hook") | JsonOutputParser()
        data = chain.invoke(common_inputs(state))
        candidates = [c for c in (data.get("hooks") if isinstance(data, dict) else data) or [] if isinstance(c, dict)]
        hook = pick_best_hook(candidates)
        if not hook:
            raise ValueError("no usable hook candidates")
        logger.info("Stage: Hook - chose %r from %d candidates", hook, len(candidates))
        return {"hook": hook, "regenerated_hooks": candidates}
    except Exception as e:  # noqa: BLE001 - the job decides how to handle a missing hook
        logger.error("Stage: Hook - failed: %s", safe_error(e))
        return {"hook": "", "hook_error": safe_error(e)}
