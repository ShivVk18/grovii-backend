from langgraph.graph import StateGraph, END

from src.ai.state import GraphState

from src.ai.nodes.hook_node import hook_node
from src.ai.nodes.hook_regenerator_node import hook_regenerator_node
from src.ai.nodes.scene_node import scene_node
from src.ai.nodes.script_node import script_node

from src.ai.nodes.caption_node import caption_node
from src.ai.nodes.hashtag_node import hashtag_node
from src.ai.nodes.music_node import music_node
from src.ai.nodes.trend_node import trend_node
from src.ai.nodes.repurpose_node import repurpose_node

from src.ai.nodes.collector_node import collector_node


builder = StateGraph(GraphState)



#################################################
# Nodes
#################################################

builder.add_node(
    "hook",
    hook_node
)

builder.add_node(
    "hook_regenerator",
    hook_regenerator_node
)

builder.add_node(
    "director",
    scene_node
)

builder.add_node(
    "script",
    script_node
)



builder.add_node(
    "caption",
    caption_node
)

builder.add_node(
    "hashtag",
    hashtag_node
)

builder.add_node(
    "music",
    music_node
)

builder.add_node(
    "trend",
    trend_node
)

builder.add_node(
    "repurpose",
    repurpose_node
)



builder.add_node(
    "collector",
    collector_node
)



#################################################
# Entry
#################################################

builder.set_entry_point(

    "hook"

)



#################################################
# Sequential
#################################################


builder.add_edge(

    "hook",

    "hook_regenerator"

)


builder.add_edge(

    "hook_regenerator",

    "director"

)



builder.add_edge(

    "director",

    "script"

)



#################################################
# Fanout
#################################################


builder.add_edge(

    "script",

    "caption"

)



builder.add_edge(

    "script",

    "hashtag"

)



builder.add_edge(

    "script",

    "music"

)



builder.add_edge(

    "script",

    "trend"

)



builder.add_edge(

    "script",

    "repurpose"

)



#################################################
# Collector
#################################################


builder.add_edge(

    "caption",

    "collector"

)


builder.add_edge(

    "hashtag",

    "collector"

)


builder.add_edge(

    "music",

    "collector"

)


builder.add_edge(

    "trend",

    "collector"

)


builder.add_edge(

    "repurpose",

    "collector"

)



#################################################
# End
#################################################


builder.add_edge(

    "collector",

    END

)




graph = builder.compile()
