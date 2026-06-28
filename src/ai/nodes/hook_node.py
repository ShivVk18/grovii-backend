import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential
)

from src.ai.prompts.hook_prompts import hook_prompt
from src.services.openai_service import openai_service


logger = logging.getLogger(__name__)

llm = openai_service.get_llm()

chain = hook_prompt | llm


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(
        multiplier=1,
        min=1,
        max=5
    )
)
def generate_hook(payload):
    return chain.invoke(payload)


def hook_node(state):

    try:

        response = generate_hook(

            {
                "idea": state["idea"],
                "goal": state["goal"],
                "tone": state["tone"],
                "audience": state["audience"],
                "platform": state["platform"]
            }

        )


        hook = response.content.strip()


        if len(hook.split()) > 15:
            raise ValueError(
                "Hook exceeds maximum word limit"
            )


        if len(hook) < 10:
            raise ValueError(
                "Hook too short"
            )


        state["hook"] = hook


        logger.info(
            f"Generated hook: {hook}"
        )


    except Exception as e:


        logger.error(
            f"Hook generation failed: {e}"
        )


        state["hook"] = ""


        state["hook_error"] = str(e)



    return state