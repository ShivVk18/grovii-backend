"""Script node: no LLM. The full voiceover script is the scene voiceovers in
order (Phase D design: scenes are the single source of truth for narration,
so the script and the per-scene lines can never disagree)."""
import logging

from src.ai.inputs import get

logger = logging.getLogger(__name__)


def script_node(state):
    scenes = get(state, "scenes", []) or []
    lines = [str(s.get("voiceover_example") or "").strip() for s in scenes if isinstance(s, dict)]
    lines = [line for line in lines if line]
    if not lines:
        return {"script": "", "script_error": "no scene voiceovers to build the script from"}
    logger.info("Stage: Script - built from %d scene voiceovers", len(lines))
    return {"script": "\n\n".join(lines)}
