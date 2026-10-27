from langchain_core.prompts import PromptTemplate

TREND_ANALYZER_TEMPLATE = """
Analyze social media trends for the given idea.
Suggest Hooks, Sounds, Editing style, Posting strategy, Transitions, and Content gaps.

Idea: {idea}
Platform: {platform}
Audience: {audience}

{format_instructions}
"""

trend_analyzer_prompt = PromptTemplate(
    template=TREND_ANALYZER_TEMPLATE,
    input_variables=["idea", "platform", "audience"],
    partial_variables={"format_instructions": ""}
)


# Wrap user text in <user_input> and add the injection-safety preamble.
from src.ai.prompt_safety import harden  # noqa: E402

trend_analyzer_prompt = harden(trend_analyzer_prompt)
