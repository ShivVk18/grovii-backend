import logging

from src.services.openai_service import openai_service
from src.ai.prompts.script_prompt import script_prompt


logger = logging.getLogger(__name__)


llm = openai_service.get_llm()

chain = script_prompt | llm


def format_scenes(scenes):


    formatted=[]


    for scene in scenes:



        formatted.append(


f"""


Scene {scene['scene_number']}


Title:
{scene['title']}



Duration:
{scene['duration']}



Camera:
{scene['camera_angle']}



Movement:
{scene['camera_movement']}



Lighting:
{scene['lighting']}



Broll:
{scene['broll']}



Voiceover:
{scene['script_segment']}




"""


)


    return "\n".join(formatted)





def script_node(state):


    try:


        formatted_scenes = format_scenes(

                state["scenes"]
        )



        response = chain.invoke(


            {

                "hook":state["hook"],


                "scenes":formatted_scenes,


                "audience":state["audience"],


                "platform":state["platform"]

            }

        )



        script = response.content.strip()




        if len(script)<100:


            raise ValueError(

                "Generated script too short"

            )




        state["script"]=script



        logger.info(

            "Script generated successfully"
        )



    except Exception as e:



        logger.error(


            f"Script generation failed : {e}"

        )



        state["script"]=""



        state["script_error"]=str(e)




    return state