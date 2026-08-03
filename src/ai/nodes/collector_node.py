from datetime import datetime, timezone


def get_state_val(state, key, default=""):
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def update_state(state, updates):
    if isinstance(state, dict):
        state.update(updates)
        return state
    else:
        return updates


def collector_node(state):
    updates = {}
    updates["status"] = "completed"
    updates["completed_at"] = datetime.now(timezone.utc).isoformat()

    updates["summary"] = {
        "scenes": len(
            get_state_val(
                state,
                "scenes",
                []
            )
        ),

        "captions": len(
            get_state_val(
                state,
                "captions",
                []
            )
        ),

        "hashtags": len(
            get_state_val(
                state,
                "hashtags",
                []
            )
        ),

        "music": len(
            get_state_val(
                state,
                "scene_music",
                []
            )
        )
    }

    return update_state(state, updates)