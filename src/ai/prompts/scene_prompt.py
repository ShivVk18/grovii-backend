from langchain_core.prompts import PromptTemplate

# The scene node is the ONE place narration is written (Phase D design:
# scenes first). The full script is built in code by joining the scene
# voiceovers, so script and scenes can never disagree.
scene_prompt = PromptTemplate(
    template="""You are a creative director planning a short-form video that a creator will film themselves, with no crew.

BRIEF
Idea: {idea}
Goal: {goal}
Style: {style}
Audience: {audience}
Platform: {platform}
Opening hook (spoken first): {hook}
Creator constraints:
{constraints}

TIMING (enforced by code)
- Total length: exactly {duration} seconds. Plan {scene_count} scenes.
- duration_seconds are whole numbers that add up to exactly {duration}.
- Spoken words: about 2.5 words per second. A scene's voiceover must fit its duration
  (at most duration_seconds x 2.5 words).

OPEN BRIEFS
If the idea is broad (for example "street food recipe" or "morning routine"), choose ONE specific,
concrete example (for example "Mumbai vada pav" or "a 6 AM routine for a student"), put it in
"chosen_example", and make every scene about that example by name. If the idea is already
specific, set "chosen_example" to null.

FOR EACH SCENE, in plain words a beginner can act on (no lens sizes, f-stops or film jargon here):
- what_to_record: the physical action to film, step by step.
- where: the exact spot to film (for example "kitchen counter next to the window").
- framing: how to hold or place the phone (for example "phone propped at chest height, close on your hands").
- voiceover: the exact words spoken in this scene. Read in order, the voiceovers form the
  complete script: they must flow as one narration with no repetition. Scene 1's voiceover
  starts with the hook, word for word.
- onscreen_text: short text overlay (max 8 words).
- tips: one practical filming tip using only the creator's equipment.
- emotion: one word.
- advanced: optional technical notes for experienced creators (camera_angle, camera_movement,
  lighting, transition, music, director_notes).
{feedback}
Return ONLY JSON:
{{"chosen_example": null, "scenes": [{{"title": "...", "duration_seconds": 0, "what_to_record": "...",
"where": "...", "framing": "...", "voiceover": "...", "onscreen_text": "...", "tips": "...",
"emotion": "...", "advanced": {{"camera_angle": "...", "camera_movement": "...", "lighting": "...",
"transition": "...", "music": "...", "director_notes": "..."}}}}]}}
""",
    input_variables=["idea", "goal", "style", "audience", "platform", "hook", "constraints",
                     "duration", "scene_count", "feedback"],
)

# Wrap user text in <user_input> and add the injection-safety preamble.
from src.ai.prompt_safety import harden  # noqa: E402

scene_prompt = harden(scene_prompt)
