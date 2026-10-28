"""Director node: plans the scenes AND writes the narration (Phase D, scenes first).

Flow: ask the model -> check the timeline in code -> if wrong, ask once more
with the problems fed back -> if still wrong, rescale durations in code.
Every scene ends up with contiguous start/end timestamps that sum exactly to
the requested duration, and scene 1's voiceover opens with the hook.
"""
import logging

from langchain_core.output_parsers import JsonOutputParser

from src.ai.inputs import common_inputs, get
from src.ai.prompts.scene_prompt import scene_prompt
from src.ai.timeline import (
    apply_timeline,
    scene_count_for,
    seconds_of,
    timeline_problems,
)
from src.services.openai_service import openai_service
from src.config.log_safety import safe_error

logger = logging.getLogger(__name__)


def build_scene_inputs(state, feedback: str = "") -> dict:
    duration = int(get(state, "duration", 30) or 30)
    return {**common_inputs(state), "duration": duration, "scene_count": scene_count_for(duration),
            "feedback": feedback}


def _ask(inputs: dict) -> dict:
    chain = scene_prompt | openai_service.get_llm("director") | JsonOutputParser()
    data = chain.invoke(inputs)
    return data if isinstance(data, dict) else {"scenes": data}


def _compose_what_to_show(sc: dict) -> str:
    action = str(sc.get("what_to_record") or sc.get("what_to_show") or "").strip()
    where = str(sc.get("where") or "").strip()
    framing = str(sc.get("framing") or "").strip()
    parts = [action]
    if where:
        parts.append(f"Where: {where}.")
    if framing:
        parts.append(f"Framing: {framing}.")
    return " ".join(p for p in parts if p)


def _normalize(data: dict) -> list[dict]:
    scenes = []
    for sc in data.get("scenes") or []:
        if not isinstance(sc, dict):
            continue
        voiceover = str(sc.get("voiceover") or sc.get("voiceover_example") or "").strip()
        what = _compose_what_to_show(sc)
        raw_advanced = sc.get("advanced")
        advanced: dict = raw_advanced if isinstance(raw_advanced, dict) else {}
        scenes.append({
            "title": str(sc.get("title") or "").strip(),
            "duration_seconds": seconds_of(sc.get("duration_seconds", sc.get("duration"))),
            "what_to_show": what,
            "what_to_record": what,
            "voiceover_example": voiceover,
            "what_to_say": voiceover,
            "onscreen_text": str(sc.get("onscreen_text") or "").strip(),
            "tips": str(sc.get("tips") or "").strip(),
            "emotion": str(sc.get("emotion") or "").strip(),
            "advanced": advanced,
            "camera_angle": advanced.get("camera_angle"),
            "camera_movement": advanced.get("camera_movement"),
            "lighting": advanced.get("lighting"),
        })
    return scenes


def _content_problems(scenes: list[dict]) -> list[str]:
    missing = [str(i) for i, s in enumerate(scenes, 1) if not s["voiceover_example"] or not s["what_to_show"]]
    return [f"Scenes {', '.join(missing)} are missing a voiceover or what_to_record."] if missing else []


def ensure_hook_opens(scenes: list[dict], hook: str) -> list[dict]:
    """Scene 1's spoken line must start with the hook (the hook IS the opening line)."""
    hook = (hook or "").strip()
    if not scenes or not hook:
        return scenes
    first = scenes[0]["voiceover_example"]
    if hook.lower().rstrip(".!?") not in first.lower():
        first = f"{hook} {first}".strip()
    return [{**scenes[0], "voiceover_example": first, "what_to_say": first}, *scenes[1:]]


def scene_node(state):
    logger.info("Stage: Scenes - started")
    duration = int(get(state, "duration", 30) or 30)
    try:
        data = _ask(build_scene_inputs(state))
        scenes = _normalize(data)
        problems = timeline_problems(scenes, duration) + _content_problems(scenes)
        adjusted = False
        if problems:
            logger.warning("Stage: Scenes - retrying with feedback: %s", problems)
            feedback = ("\nYOUR PREVIOUS ANSWER HAD THESE PROBLEMS. FIX THEM:\n- " + "\n- ".join(problems) + "\n")
            try:
                retry_data = _ask(build_scene_inputs(state, feedback))
                retry_scenes = _normalize(retry_data)
                if retry_scenes and not _content_problems(retry_scenes):
                    data, scenes = retry_data, retry_scenes
            except Exception as e:  # noqa: BLE001 - fall back to rescaling the first answer
                logger.warning("Stage: Scenes - retry failed (%s); rescaling first answer", safe_error(e))
            adjusted = bool(timeline_problems(scenes, duration))
        if not scenes:
            raise ValueError("model returned no scenes")
        scenes = ensure_hook_opens(apply_timeline(scenes, duration), get(state, "hook"))
        logger.info("Stage: Scenes - %d scenes, rescaled=%s", len(scenes), adjusted)
        return {"scenes": scenes, "timeline_adjusted": adjusted,
                "brief_choice": (data.get("chosen_example") or None)}
    except Exception as e:  # noqa: BLE001 - the job fails closed on empty scenes
        logger.error("Stage: Scenes - failed: %s", safe_error(e))
        return {"scenes": [], "scene_error": safe_error(e)}
