from src.ai.prompts.repurpose_prompt import repurpose_content_prompt
from src.services.openai_service import openai_service
from langchain_core.output_parsers import JsonOutputParser
from src.Schemas.repurpose import RepurposeOutput

llm = openai_service.get_llm()
parser = JsonOutputParser(pydantic_object=RepurposeOutput)
chain = repurpose_content_prompt | llm | parser

def repurpose_node(state):
    response = chain.invoke({
        "script": state.get("script", ""),
        "format_instructions": parser.get_format_instructions()
    })
    
    state["repurposed_content"] = response
    return state
