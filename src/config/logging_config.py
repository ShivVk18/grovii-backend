"""Structured logging (Phase G).

Every log line can carry the request id of the API call that caused it, and the
job id when it runs inside a worker. In production lines are JSON, one object
per line, so a log platform can search and chart them (e.g. event=job_finished).
"""
import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

from src.config import ops_settings
from src.config.log_safety import install_redaction

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
job_id_var: ContextVar[str | None] = ContextVar("job_id", default=None)

# Attributes every LogRecord has; anything else was passed via `extra=`.
_STANDARD = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime", "taskName", "color_message"}


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = request_id_var.get()
        if not getattr(record, "job_id", None):
            record.job_id = job_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or request_id_var.get(),
            "job_id": getattr(record, "job_id", None) or job_id_var.get(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD and key not in out:
                out[key] = value
        if record.exc_info:
            # Type and stack only; the message is already redacted at record creation.
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps({k: v for k, v in out.items() if v is not None}, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("%(asctime)s [%(levelname)s] %(name)s: %(message)s [req=%(request_id)s job=%(job_id)s]")


def setup_logging() -> None:
    """Configure the root logger once (API and worker). Idempotent."""
    install_redaction()
    root = logging.getLogger()
    if any(getattr(h, "_grovii", False) for h in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler._grovii = True  # type: ignore[attr-defined]
    handler.addFilter(ContextFilter())
    handler.setFormatter(JsonFormatter() if ops_settings.LOG_FORMAT == "json" else TextFormatter())
    root.handlers = [h for h in root.handlers if not isinstance(h, logging.StreamHandler)] + [handler]
    root.setLevel(ops_settings.LOG_LEVEL)
    # uvicorn's own handlers would print a second, unstructured copy.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "rq.worker"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
