"""Scene timeline rules enforced in code (QUAL-02).

The LLM proposes a duration per scene; code checks that they add up to the
requested video length and, as a last resort, rescales them. Every scene gets
contiguous start/end timestamps.
"""
import re

TOLERANCE = 0.10  # same +/-10% the Phase 5 validator uses
MIN_SCENES, MAX_SCENES, SECONDS_PER_SCENE = 3, 8, 6


def scene_count_for(duration: int) -> int:
    """About one scene every 6 seconds, between 3 and 8 scenes."""
    return max(MIN_SCENES, min(MAX_SCENES, round(duration / SECONDS_PER_SCENE)))


def seconds_of(value) -> int:
    """Parse 6, 6.0, "6", "6s" or "6 seconds" to whole seconds (0 if unknown)."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, round(value))
    if isinstance(value, str):
        m = re.search(r"\d+(?:\.\d+)?", value)
        return round(float(m.group())) if m else 0
    return 0


def timeline_problems(scenes: list[dict], target: int) -> list[str]:
    """Plain-language problems the model can be told to fix ([] if fine)."""
    if not scenes:
        return ["There are no scenes."]
    problems = []
    durations = [seconds_of(s.get("duration_seconds", s.get("duration"))) for s in scenes]
    if any(d < 1 for d in durations):
        problems.append("Every scene needs a duration of at least 1 second.")
    total = sum(durations)
    if abs(total - target) > target * TOLERANCE:
        problems.append(
            f"Scene durations sum to {total} seconds but the video must be {target} seconds; "
            f"make duration_seconds add up to exactly {target}."
        )
    return problems


def _rescale(durations: list[int], target: int) -> list[int]:
    """Scale to integers that sum exactly to target (largest remainder), each >= 1."""
    n = len(durations)
    weights = [max(d, 1) for d in durations]
    total = sum(weights)
    raw = [w * target / total for w in weights]
    out = [max(1, int(r)) for r in raw]
    # Distribute the remaining seconds to the largest fractional parts.
    diff = target - sum(out)
    order = sorted(range(n), key=lambda i: raw[i] - int(raw[i]), reverse=diff > 0)
    i = 0
    while diff != 0 and n:
        j = order[i % n]
        if diff > 0:
            out[j] += 1
            diff -= 1
        elif out[j] > 1:
            out[j] -= 1
            diff += 1
        i += 1
    return out


def apply_timeline(scenes: list[dict], target: int) -> list[dict]:
    """Return scenes with exact integer durations summing to target, plus
    scene_number, start_seconds and end_seconds."""
    durations = [seconds_of(s.get("duration_seconds", s.get("duration"))) for s in scenes]
    if sum(durations) != target:
        durations = _rescale(durations, target)
    out, start = [], 0
    for i, (scene, d) in enumerate(zip(scenes, durations), 1):
        out.append({**scene, "scene_number": i, "duration_seconds": d, "duration": str(d),
                    "start_seconds": start, "end_seconds": start + d})
        start += d
    return out
