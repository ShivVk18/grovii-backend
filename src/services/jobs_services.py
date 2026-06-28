from src.ai.graph import graph

from src.database import SessionLocal

from src.repositories.storyboard_repository import (
    save_graph_result
)

from src.repositories.job_repository import (

    get_job,

    mark_processing,

    mark_completed,

    mark_failed

)


def generate_storyboard_job(

        payload,

        storyboard_id,

        job_id

):


    db = SessionLocal()


    try:


        ################################################
        # Fetch Job
        ################################################
        print("STEP 1")
        job = get_job(

            db,

            job_id

        )


        if not job:
            raise Exception(

                "Job not found"

            )


        ################################################
        # Processing
        ################################################
        print("STEP 2")
        mark_processing(

            db,

            job

        )



        ################################################
        # LangGraph
        ################################################
        print("STEP 3")
        state = graph.invoke(

            payload

        )



        ################################################
        # Persist
        ################################################
        print("STEP 4")
        save_graph_result(

            db,

            storyboard_id,

            state

        )



        ################################################
        # Complete
        ################################################
        print("STEP 5")
        mark_completed(

            db,

            job

        )



        return state



    except Exception as e:


        ################################################
        # Failed
        ################################################


        if 'job' in locals():

            mark_failed(

                db,

                job,

                str(e)

            )


        raise e


    finally:


        db.close()
