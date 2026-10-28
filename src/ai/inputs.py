"""Inputs every prompt receives, so language, tone and the brief reach every node."""


def get(state, key, default=""):
    if isinstance(state, dict):
        value = state.get(key, default)
    else:
        value = getattr(state, key, default)
    return default if value is None else value


def constraints_text(state) -> str:
    parts = []
    if get(state, "faceless", False):
        parts.append("FACELESS: the creator's face must never appear. Use hands, POV shots, objects, "
                     "screen recordings or the environment instead.")
    if get(state, "location", ""):
        parts.append(f"LOCATION: everything is filmed at: {get(state, 'location')}.")
    if get(state, "equipment", ""):
        parts.append(f"EQUIPMENT: only this gear is available: {get(state, 'equipment')}. "
                     "Do not suggest anything else.")
    return "\n".join(parts) or "None. Assume a smartphone and a normal home or everyday location."


def common_inputs(state) -> dict:
    return {
        "idea": get(state, "idea"),
        "goal": get(state, "goal"),
        "tone": get(state, "tone"),
        "style": get(state, "style"),
        "audience": get(state, "audience"),
        "platform": get(state, "platform"),
        "duration": get(state, "duration", 30),
        "language": get(state, "language", "English") or "English",
        "hook": get(state, "hook"),
        "script": get(state, "script"),
        "constraints": constraints_text(state),
        "brief_choice": get(state, "brief_choice") or "none",
    }
