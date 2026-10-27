from src.ai.prompts.repurpose_prompt import repurpose_content_prompt
from src.services.openai_service import openai_service
from langchain_core.output_parsers import JsonOutputParser
from src.Schemas.repurpose import RepurposeOutput


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


def repurpose_node(state):
    llm = openai_service.get_llm("repurpose")
    parser = JsonOutputParser(pydantic_object=RepurposeOutput)
    chain = repurpose_content_prompt | llm | parser

    response = chain.invoke({
        "script": get_state_val(state, "script"),
        "format_instructions": parser.get_format_instructions()
    })
    
    updates = {
        "repurposed_content": response
    }
    return update_state(state, updates)

