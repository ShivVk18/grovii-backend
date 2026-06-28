import logging


from src.ai.prompts.scene_prompt import scene_prompt
from src.Schemas.scene import SceneList

from src.services.openai_service import openai_service


from langchain_core.output_parsers import (
        PydanticOutputParser
)



logger = logging.getLogger(__name__)


llm = openai_service.get_llm()



parser = PydanticOutputParser(

            pydantic_object=SceneList
)



chain = scene_prompt | llm | parser





def scene_node(state):



    try:



        scenes = chain.invoke(

            {


                "idea":state['idea'],


                "hook":state['hook'],


                "tone":state['tone'],


                "audience":state['audience']

            }

        )


        if len(state['scenes']) != 5:


         raise Exception(
        "Expected exactly 5 scenes"
         )

        state['scenes'] = [

            scene.model_dump()

            for scene in scenes.scenes

        ]



        logger.info(

            f"Generated {len(state['scenes'])} scenes"

        )




    except Exception as e:



        logger.error(


            f"Scene generation failed : {e}"

        )




        state['scenes']=[]



        state['scene_error']=str(e)




    return state