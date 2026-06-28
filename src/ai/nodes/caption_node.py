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


llm = openai_service.get_llm()

parser = JsonOutputParser()

chain = caption_prompt | llm | parser


@retry(

    stop=stop_after_attempt(3),

    wait=wait_exponential(

        multiplier=1,

        min=1,

        max=5

    )

)
def generate_captions(payload):

    return chain.invoke(payload)


def caption_node(state):


    try:


        captions = generate_captions(

            {

                "script": state["script"],

                "tone": state["tone"],

                "audience": state["audience"]

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


        state["captions"] = cleaned


        logger.info(

            f"Generated {len(cleaned)} captions"

        )



    except Exception as e:


        logger.error(

            f"Caption generation failed: {e}"

        )


        state["captions"] = []


        state["caption_error"] = str(e)



    return state
