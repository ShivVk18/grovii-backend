from datetime import datetime



def collector_node(state):


    state["status"]="completed"



    state["completed_at"]=datetime.utcnow().isoformat()



    state["summary"]={

        "scenes":len(

            state.get(

                "scenes",

                []

            )

        ),




        "captions":len(

            state.get(

                "captions",

                []

            )

        ),




        "hashtags":len(

            state.get(

                "hashtags",

                []

            )

        ),



        "music":len(

            state.get(

                "scene_music",

                []

            )

        )


    }



    return state