"""Error tracking with Sentry (Phase G): off unless SENTRY_DSN is set.

Nothing personal or secret leaves the server: request bodies (ideas, passwords),
cookies, auth headers, emails and any prompt/idea/script fields are removed in
`scrub_event` before an event is sent.
"""
import logging

from src.config import ops_settings
from src.config.log_safety import redact

logger = logging.getLogger("grovii.observability")

_SENSITIVE_KEYS = {"password", "current_password", "new_password", "idea", "prompt", "script", "hook",
                   "audience", "token", "access_token", "authorization", "cookie", "set-cookie",
                   "x-csrf-token", "x-grovii-proxy-secret", "email"}
_KEEP_HEADERS = {"user-agent", "content-type", "content-length", "x-request-id", "accept"}


def _scrub(value):
    if isinstance(value, dict):
        return {k: ("[removed]" if str(k).lower() in _SENSITIVE_KEYS else _scrub(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, str):
        return redact(value)
    return value


def scrub_event(event, hint):
    request = event.get("request") or {}
    request.pop("data", None)
    request.pop("cookies", None)
    request.pop("query_string", None)
    headers = request.get("headers") or {}
    request["headers"] = {k: v for k, v in headers.items() if k.lower() in _KEEP_HEADERS}
    if request:
        event["request"] = request
    if "user" in event:
        event["user"] = {"id": event["user"].get("id")} if event["user"].get("id") else {}
    for key in ("extra", "contexts", "tags"):
        if key in event:
            event[key] = _scrub(event[key])
    for bc in (event.get("breadcrumbs") or {}).get("values", []) or []:
        bc["message"] = redact(str(bc.get("message") or ""))
        bc.pop("data", None)
    return event


def init_sentry(component: str = "api") -> bool:
    dsn = ops_settings.SENTRY_DSN
    import os

    dsn = os.getenv("SENTRY_DSN", dsn)
    if not dsn:
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("APP_ENV", "development"),
            release=ops_settings.RELEASE,
            send_default_pii=False,
            traces_sample_rate=ops_settings.SENTRY_TRACES_SAMPLE_RATE,
            before_send=scrub_event,
            max_request_body_size="never",
        )
        sentry_sdk.set_tag("component", component)
        return True
    except Exception as e:  # noqa: BLE001 - error tracking must never stop the app
        logger.error("Sentry init failed: %s", type(e).__name__)
        return False
