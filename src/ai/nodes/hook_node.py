from src.ai.prompts.hook_prompts import hook_prompt
from src.services.openai_service import openai_service

llm = openai_service.get_llm()

chain = hook_prompt | llm


def hook_node(state):

    response = chain.invoke(

        {

            "idea": state["idea"],

            "goal": state["goal"],

            "tone": state["tone"],

            "audience": state["audience"],

            "platform": state["platform"]

        }

    )


    hook = response.content.strip()


    state["hook"] = hook


    return state