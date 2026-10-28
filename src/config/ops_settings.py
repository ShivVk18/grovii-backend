"""Operations settings (Phase G), all from the environment. Read at call time
so tests and live config changes take effect without re-importing."""
import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


# Logs: "json" (default in production) or "text" (default in development).
LOG_FORMAT = os.getenv("LOG_FORMAT", "json" if os.getenv("APP_ENV", "").lower() == "production" else "text").lower()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# /metrics is disabled unless a token is set; scrapers send "Authorization: Bearer <token>".
METRICS_TOKEN = os.getenv("METRICS_TOKEN", "")

# Alerts (checked every REAPER_INTERVAL_SECONDS by the worker's background loop).
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")   # e.g. a Slack incoming webhook
ALERT_WINDOW_MINUTES = _int("ALERT_WINDOW_MINUTES", 15)
ALERT_FAILED_JOBS = _int("ALERT_FAILED_JOBS", 5)          # failed jobs within the window
ALERT_QUEUE_BACKLOG = _int("ALERT_QUEUE_BACKLOG", 20)     # waiting jobs
ALERT_SPEND_FRACTION = _float("ALERT_SPEND_FRACTION", 0.8)  # of DAILY_SPEND_LIMIT_USD
ALERT_COOLDOWN_SECONDS = _int("ALERT_COOLDOWN_SECONDS", 1800)

# Error tracking (off unless set).
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
SENTRY_TRACES_SAMPLE_RATE = _float("SENTRY_TRACES_SAMPLE_RATE", 0.0)
RELEASE = os.getenv("RELEASE") or os.getenv("RENDER_GIT_COMMIT", "")[:12] or "dev"
