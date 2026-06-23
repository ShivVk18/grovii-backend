from langgraph.graph import StateGraph, END

from src.ai.state import GraphState

from src.ai.nodes.hook_node import hook_node
from src.ai.nodes.scene_node import scene_node

from src.ai.nodes.script_node import script_node
from src.ai.nodes.caption_node import caption_node

builder = StateGraph(GraphState)

# Nodes
builder.add_node(
    "hook",
    hook_node
)

builder.add_node(
    "scene",
    scene_node
)

builder.add_node(
    'script',
    script_node
)

builder.add_node(

"caption",

caption_node

)

builder.set_entry_point("hook")



builder.add_edge(

"hook",

"scene"

)



builder.add_edge(

"scene",

"script"

)



builder.add_edge(

"script",

"caption"

)

builder.add_edge(
    "caption",
    END
)

# Compile
graph = builder.compile()