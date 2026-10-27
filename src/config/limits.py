"""Cost and abuse limits. Every value can be overridden with an environment
variable of the same name; defaults are chosen from the eval measurements
(see fix/phase_b.md for the reasoning behind each number)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = int(raw)
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = float(raw)
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


# ---------------------------------------------------------------- credits ----
CREDITS_PER_GENERATION = _int("CREDITS_PER_GENERATION", 1)
# A user may have at most this many generations queued or running at once.
MAX_ACTIVE_JOBS_PER_USER = _int("MAX_ACTIVE_JOBS_PER_USER", 2)
# Jobs older than this no longer count as "active" for the cap, so a job that
# got stuck (no reaper until Phase C) cannot lock a user out forever.
ACTIVE_JOB_WINDOW_MINUTES = _int("ACTIVE_JOB_WINDOW_MINUTES", 30)

# ------------------------------------------------------------ rate limits ----
# Format: (max requests, window in seconds)
RATE_GENERATE_PER_USER = (_int("RATE_GENERATE_PER_USER", 10), 3600)
RATE_GENERATE_PER_IP = (_int("RATE_GENERATE_PER_IP", 30), 3600)
RATE_LOGIN_PER_IP = (_int("RATE_LOGIN_PER_IP", 10), 60)
RATE_LOGIN_PER_EMAIL = (_int("RATE_LOGIN_PER_EMAIL", 5), 900)
RATE_REGISTER_PER_IP = (_int("RATE_REGISTER_PER_IP", 5), 3600)
RATE_CREATE_PER_USER = (_int("RATE_CREATE_PER_USER", 30), 60)

# -------------------------------------------------------------------- LLM ----
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
# Optional: route LLM calls through a proxy or compatible endpoint.
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or None
LLM_TIMEOUT_SECONDS = _float("LLM_TIMEOUT_SECONDS", 60.0)
LLM_MAX_RETRIES = _int("LLM_MAX_RETRIES", 2)

# Max output tokens per graph node. Measured output (max of 30 eval runs):
# hook 16, regenerated hooks ~70, scenes 2272, script 198, captions 174,
# hashtags 86, music 100, repurpose 599. Caps leave 2x+ headroom; the script
# and scenes caps also leave room for longer videos (up to 180s).
NODE_MAX_OUTPUT_TOKENS: dict[str, int] = {
    "hook": 150,
    "hook_regenerator": 800,
    "director": 5000,
    "script": 1500,
    "caption": 800,
    "hashtag": 500,
    "music": 1500,
    "trend": 1000,
    "repurpose": 2000,
}
DEFAULT_MAX_OUTPUT_TOKENS = 1000

# Total tokens (input + output) one generation job may use. Average measured
# use is ~6.5k; the budget allows retries without letting one job run away.
JOB_TOKEN_BUDGET = _int("JOB_TOKEN_BUDGET", 40_000)

# Global spend ceiling across all users, per UTC day. When reached, new
# generations are refused with 503 and a CRITICAL log line is emitted.
DAILY_SPEND_LIMIT_USD = _float("DAILY_SPEND_LIMIT_USD", 20.0)

# USD per 1M tokens. Check your provider's current price list; these are the
# rates used in eval/phase8_performance.md for gpt-4o.
PRICE_INPUT_PER_M = _float("LLM_PRICE_INPUT_PER_M", 2.50)
PRICE_OUTPUT_PER_M = _float("LLM_PRICE_OUTPUT_PER_M", 10.00)


def estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens * PRICE_INPUT_PER_M + completion_tokens * PRICE_OUTPUT_PER_M) / 1_000_000


# Worst case one in-flight job can still spend; reserved against the daily
# ceiling until the job finishes and its real cost is known.
JOB_COST_RESERVE_USD = estimate_cost_usd(0, JOB_TOKEN_BUDGET)
