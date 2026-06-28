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
