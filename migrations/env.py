from logging.config import fileConfig
import os

from sqlalchemy import create_engine
from sqlalchemy import pool

from alembic import context

from src.config.config import settings
from dotenv import load_dotenv

load_dotenv()



config = context.config


DATABASE_URL = settings.DATABASE_URL


config.set_main_option(

        "sqlalchemy.url",

       DATABASE_URL.replace("%", "%%")

)


if config.config_file_name:
    fileConfig(
        config.config_file_name
    )


#################################################
# MODELS
#################################################

from src.database import Base


from src.models.users import User
from src.models.storyboard import Storyboard
from src.models.scenes import Scene

from src.models.caption import Caption
from src.models.hashtag import Hashtag
from src.models.hook import Hook

from src.models.music import MusicSuggestion
from src.models.trend import Trend
from src.models.repurpose import RepurposeContent




target_metadata = Base.metadata




def run_migrations_offline():



    url = config.get_main_option(

            "sqlalchemy.url"

    )



    context.configure(

        url=url,

        target_metadata=target_metadata,

        literal_binds=True,

        dialect_opts={

            "paramstyle":"named"

        }

    )



    with context.begin_transaction():

        context.run_migrations()





def run_migrations_online():



    connectable = create_engine(
    DATABASE_URL,
    poolclass=pool.NullPool
)



    with connectable.connect() as connection:



        context.configure(


            connection=connection,


            target_metadata=target_metadata

        )



        with context.begin_transaction():



            context.run_migrations()




if context.is_offline_mode():

    run_migrations_offline()


else:

    run_migrations_online()
