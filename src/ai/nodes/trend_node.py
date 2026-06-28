from src.ai.prompts.trend_prompt import trend_analyzer_prompt
from src.services.openai_service import openai_service
from langchain_core.output_parsers import JsonOutputParser
from src.Schemas.trend import TrendAnalyzerOutput

llm = openai_service.get_llm()
parser = JsonOutputParser(pydantic_object=TrendAnalyzerOutput)
chain = trend_analyzer_prompt | llm | parser

def trend_node(state):
    response = chain.invoke({
        "idea": state.get("idea", ""),
        "platform": state.get("platform", ""),
        "audience": state.get("audience", ""),
        "format_instructions": parser.get_format_instructions()
    })
    
    state["trends"] = response
    return state
