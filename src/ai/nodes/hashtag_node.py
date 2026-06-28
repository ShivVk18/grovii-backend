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


llm = openai_service.get_llm()


parser = JsonOutputParser()


chain = hashtag_prompt | llm | parser



@retry(

    stop=stop_after_attempt(3),

    wait=wait_exponential(

        multiplier=1,

        min=1,

        max=5

    )

)

def generate_hashtags(payload):


    return chain.invoke(payload)





def hashtag_node(state):



    try:



        hashtags = generate_hashtags(


            {


                "script":state["script"],


                "audience":state["audience"]

            }

        )



        cleaned = []

        seen = set()



        for tag in hashtags:



            hashtag = tag["hashtag"].lower()



            if hashtag not in seen:



                cleaned.append(tag)



                seen.add(hashtag)




        state["hashtags"] = cleaned




        logger.info(

            f"Generated {len(cleaned)} hashtags"

        )



    except Exception as e:



        logger.error(

            f"Hashtag generation failed {e}"

        )



        state["hashtags"] = []


        state["hashtag_error"] = str(e)




    return state