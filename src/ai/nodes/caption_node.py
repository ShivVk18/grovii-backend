from src.ai.prompts.caption_prompts import caption_prompt
from src.services.openai_service import openai_service

from langchain_core.output_parsers import JsonOutputParser


llm = openai_service.get_llm()

parser = JsonOutputParser()


chain = caption_prompt | llm | parser




def caption_node(state):



    captions = chain.invoke(

        {


            "script":state["script"],

            "tone":state["tone"],


            "audience":state["audience"]

        }

    )



    state["captions"] = captions



    return state