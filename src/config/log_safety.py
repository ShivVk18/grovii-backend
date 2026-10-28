"""Keep secrets and creator content out of logs (Phase F).

* `safe_error(e)`: what to log for an exception from an AI step. Parser and
  validation errors embed the model's whole reply (which can repeat the
  creator's idea), so only their type is logged. Other errors keep a short,
  single-line message.
* `RedactingFilter`: last line of defence on every log handler; masks bearer
  tokens, JWTs and password=... pairs in any message.
"""
import json
import logging
import re

# Exceptions whose message contains generated or user text.
_CONTENT_CARRYING = ("OutputParserException", "JSONDecodeError", "ValidationError", "CriticalOutputMissing")
_MAX = 160

_PATTERNS = [
    (re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "[REDACTED_JWT]"),
    (re.compile(r"(?i)(password|passwd|pwd|secret|api[_-]?key|token)(\"?\s*[:=]\s*\"?)([^\s\"',;&]+)"), r"\1\2[REDACTED]"),
]


def redact(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


def safe_error(e: BaseException) -> str:
    name = type(e).__name__
    if name in _CONTENT_CARRYING or isinstance(e, (json.JSONDecodeError, ValueError)) and "json" in name.lower():
        return name
    msg = " ".join(str(e).split())[:_MAX]
    return f"{name}: {redact(msg)}" if msg else name


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - never break logging
            return True
        cleaned = redact(message)
        if cleaned != message:
            record.msg, record.args = cleaned, None
        return True


_installed = False


def install_redaction() -> None:
    """Redact every log record when it is created, so handlers added later
    (uvicorn, rq) are covered too."""
    global _installed
    if _installed:
        return
    base_factory = logging.getLogRecordFactory()
    redactor = RedactingFilter()

    def factory(*args, **kwargs):
        record = base_factory(*args, **kwargs)
        redactor.filter(record)
        return record

    logging.setLogRecordFactory(factory)
    _installed = True
