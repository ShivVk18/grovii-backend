from langchain_core.prompts import PromptTemplate

# One call returns several scored candidates; code picks the best
# (src/ai/quality.py:pick_best_hook). This replaces the old second
# "hook regenerator" LLM call.
hook_prompt = PromptTemplate(
    template="""You write opening hooks for short-form {platform} videos.

INPUT
Idea: {idea}
Goal: {goal}
Audience: {audience}
Video length: {duration} seconds

TASK
Write 4 different hooks for this video. Each hook:
- is spoken in the first 3 seconds: 4 to 12 words,
- is specific to this idea (name the concrete thing, number or mistake), not generic hype,
- sounds natural said out loud on camera; no clickbait, no "you won't believe".
Give each a score from 0 to 100 for how well it would stop a scroll for this audience.

Return ONLY JSON:
{{"hooks": [{{"hook": "...", "framework": "curiosity | contrarian | mistake | number | story | question", "score": 0}}]}}
""",
    input_variables=["platform", "idea", "goal", "audience", "duration"],
)

# Wrap user text in <user_input> and add the injection-safety preamble.
from src.ai.prompt_safety import harden  # noqa: E402

hook_prompt = harden(hook_prompt)
