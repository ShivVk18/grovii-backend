from langchain_core.prompts import PromptTemplate

REPURPOSE_CONTENT_TEMPLATE = """
Repurpose the following video script into other formats.
Generate content for:
- LinkedIn post
- Twitter Thread
- Carousel text
- Blog Outline
- Email Newsletter

Original Script:
{script}

{format_instructions}
"""

repurpose_content_prompt = PromptTemplate(
    template=REPURPOSE_CONTENT_TEMPLATE,
    input_variables=["script"],
    partial_variables={"format_instructions": ""}
)


# Wrap user text in <user_input> and add the injection-safety preamble.
from src.ai.prompt_safety import harden  # noqa: E402

repurpose_content_prompt = harden(repurpose_content_prompt)
