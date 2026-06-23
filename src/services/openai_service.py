from langchain_openai import ChatOpenAI

from src.config.config import settings

class OpenAiService:
    def __init__ (self):
        self.llm = ChatOpenAI(
            api_key= settings.OPENAI_API_KEY,
            model="gpt-4o",
             temperature=.7
        )
        
    def get_llm(self):
          return self.llm
        
        
openai_service = OpenAiService()
