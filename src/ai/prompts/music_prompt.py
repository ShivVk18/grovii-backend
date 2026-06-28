from langchain_core.prompts import PromptTemplate

MUSIC_SUGGESTION_TEMPLATE = """
Suggest music for the following scenes.
For each scene provide: Genre, Mood, BPM, Transition, and Timing.

Tone: {tone}
Platform: {platform}

Scenes:
{scenes}

{format_instructions}
"""

music_suggestion_prompt = PromptTemplate(
    template=MUSIC_SUGGESTION_TEMPLATE,
    input_variables=["tone", "platform", "scenes"],
    partial_variables={"format_instructions": ""}
)
