from src.ai.prompts.hook_regenerator_prompt import hook_regenerator_prompt
from src.services.openai_service import openai_service
from langchain_core.output_parsers import JsonOutputParser
from src.Schemas.hook import HookRegeneratorOutput

llm = openai_service.get_llm()
parser = JsonOutputParser(pydantic_object=HookRegeneratorOutput)
chain = hook_regenerator_prompt | llm | parser

def hook_regenerator_node(state):
    response = chain.invoke({
        "idea": state.get("idea", ""),
        "audience": state.get("audience", ""),
        "tone": state.get("tone", ""),
        "platform": state.get("platform", ""),
        "hook": state.get("hook", ""),
        "format_instructions": parser.get_format_instructions()
    })
    
    state["regenerated_hooks"] = response.get("regenerated_hooks", [])
    return state
