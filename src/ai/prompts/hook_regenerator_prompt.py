from langchain_core.prompts import PromptTemplate

HOOK_REGENERATOR_TEMPLATE = """
Generate 5 viral hooks for the following idea.
The hooks must be under 12 words.
Use the following styles: Curiosity, Emotional, Contrarian, Storytelling, FOMO.

Idea: {idea}
Audience: {audience}
Tone: {tone}
Platform: {platform}
Original Hook: {hook}

{format_instructions}
"""

hook_regenerator_prompt = PromptTemplate(
    template=HOOK_REGENERATOR_TEMPLATE,
    input_variables=["idea", "audience", "tone", "platform", "hook"],
    partial_variables={"format_instructions": ""}
)
