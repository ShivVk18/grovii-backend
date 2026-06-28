from src.ai.prompts.music_prompt import music_suggestion_prompt
from src.services.openai_service import openai_service
from langchain_core.output_parsers import JsonOutputParser
from src.Schemas.music import MusicSuggestionOutput

llm = openai_service.get_llm()
parser = JsonOutputParser(pydantic_object=MusicSuggestionOutput)
chain = music_suggestion_prompt | llm | parser

def music_node(state):
    response = chain.invoke({
        "tone": state.get("tone", ""),
        "platform": state.get("platform", ""),
        "scenes": state.get("scenes", []),
        "format_instructions": parser.get_format_instructions()
    })
    
    state["scene_music"] = response.get("scene_music", [])
    return state
