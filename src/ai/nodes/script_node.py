from src.services.openai_service import openai_service

from src.ai.prompts.script_prompt import script_prompt



llm = openai_service.get_llm()


chain = script_prompt | llm




def script_node(state):



    response = chain.invoke(

        {


        "hook":state["hook"],



        "scenes":str(state["scenes"]),



        "audience":state["audience"],



        "platform":state["platform"]

        }

    )



    state["script"] = response.content.strip()



    return state