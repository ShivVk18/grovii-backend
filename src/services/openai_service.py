from langchain_openai import ChatOpenAI

from src.config.config import settings


class OpenAiService:
    def get_llm(self, model: str = "gpt-4o", temperature: float = 0.7) -> ChatOpenAI:
        """Factory method to create a new instance of ChatOpenAI client on demand."""
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=model,
            temperature=temperature
        )


openai_service = OpenAiService()

