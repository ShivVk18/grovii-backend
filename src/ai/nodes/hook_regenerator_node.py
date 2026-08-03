from src.ai.prompts.hook_regenerator_prompt import hook_regenerator_prompt
from src.services.openai_service import openai_service
from langchain_core.output_parsers import JsonOutputParser
from src.Schemas.hook import HookRegeneratorOutput


def get_state_val(state, key, default=""):
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def update_state(state, updates):
    if isinstance(state, dict):
        state.update(updates)
        return state
    else:
        return updates


def hook_regenerator_node(state):
    llm = openai_service.get_llm()
    parser = JsonOutputParser(pydantic_object=HookRegeneratorOutput)
    chain = hook_regenerator_prompt | llm | parser

    response = chain.invoke({
        "idea": get_state_val(state, "idea"),
        "audience": get_state_val(state, "audience"),
        "tone": get_state_val(state, "tone"),
        "platform": get_state_val(state, "platform"),
        "hook": get_state_val(state, "hook"),
        "format_instructions": parser.get_format_instructions()
    })
    
    updates = {
        "regenerated_hooks": response.get("regenerated_hooks", [])
    }
    return update_state(state, updates)

