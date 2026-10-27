from src.ai.prompts.trend_prompt import trend_analyzer_prompt
from src.services.openai_service import openai_service
from langchain_core.output_parsers import JsonOutputParser
from src.Schemas.trend import TrendAnalyzerOutput


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


def trend_node(state):
    llm = openai_service.get_llm("trend")
    parser = JsonOutputParser(pydantic_object=TrendAnalyzerOutput)
    chain = trend_analyzer_prompt | llm | parser

    response = chain.invoke({
        "idea": get_state_val(state, "idea"),
        "platform": get_state_val(state, "platform"),
        "audience": get_state_val(state, "audience"),
        "format_instructions": parser.get_format_instructions()
    })
    
    updates = {
        "trends": response
    }
    return update_state(state, updates)

