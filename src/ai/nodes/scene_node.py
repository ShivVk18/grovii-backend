from src.ai.prompts.scene_prompt import scene_prompt


from src.services.openai_service import openai_service

from langchain_core.output_parsers import JsonOutputParser

llm=openai_service.get_llm()

parser=JsonOutputParser() 

chain=scene_prompt|llm|parser


def scene_node(state):



    scenes=chain.invoke(

        {

            'idea':state['idea'],

            'hook':state['hook'],

            'tone':state['tone'],

            'audience':state['audience']

        }

    )


    print(scenes)
    state['scenes']=scenes



    return state